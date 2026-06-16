import json
import mimetypes
import os
import secrets
import time
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .agent.agent import EnterpriseAgent
from .agent.memory import list_runs, list_steps
from .agent.tools import call_tool, list_tools
from .database import DEFAULT_DB_PATH, connect, initialize_database, row_to_dict, rows_to_list
from .security import ROLE_LABELS, can_access, hash_password, verify_password


PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR / "app" / "static"
SESSION_COOKIE = "enterprise_session"
SESSION_TTL_SECONDS = 8 * 60 * 60
SESSIONS = {}

ALL_ROLES = ("admin", "manager", "finance", "staff")

RESOURCE_CONFIG = {
    "customers": {
        "table": "customers",
        "fields": ["name", "industry", "contact_name", "phone", "email", "status", "owner_id"],
        "required": ["name"],
        "list_sql": """
            SELECT c.*, u.display_name AS owner_name
            FROM customers c
            LEFT JOIN users u ON u.id = c.owner_id
            ORDER BY c.updated_at DESC, c.id DESC
        """,
        "roles": {
            "GET": ALL_ROLES,
            "POST": ("admin", "manager", "staff"),
            "PUT": ("admin", "manager", "staff"),
            "DELETE": ("admin", "manager"),
        },
    },
    "projects": {
        "table": "projects",
        "fields": ["customer_id", "name", "stage", "budget", "start_date", "end_date", "owner_id", "risk_level"],
        "required": ["customer_id", "name"],
        "list_sql": """
            SELECT p.*, c.name AS customer_name, u.display_name AS owner_name
            FROM projects p
            JOIN customers c ON c.id = p.customer_id
            LEFT JOIN users u ON u.id = p.owner_id
            ORDER BY p.updated_at DESC, p.id DESC
        """,
        "roles": {
            "GET": ALL_ROLES,
            "POST": ("admin", "manager"),
            "PUT": ("admin", "manager"),
            "DELETE": ("admin", "manager"),
        },
    },
    "contracts": {
        "table": "contracts",
        "fields": ["project_id", "contract_no", "amount", "status", "sign_date", "due_date", "payment_status"],
        "required": ["project_id", "contract_no"],
        "list_sql": """
            SELECT ct.*, p.name AS project_name, c.name AS customer_name
            FROM contracts ct
            JOIN projects p ON p.id = ct.project_id
            JOIN customers c ON c.id = p.customer_id
            ORDER BY ct.updated_at DESC, ct.id DESC
        """,
        "roles": {
            "GET": ALL_ROLES,
            "POST": ("admin", "manager", "finance"),
            "PUT": ("admin", "manager", "finance"),
            "DELETE": ("admin", "manager"),
        },
    },
    "tickets": {
        "table": "tickets",
        "fields": ["project_id", "title", "priority", "status", "assignee_id", "description"],
        "required": ["project_id", "title"],
        "list_sql": """
            SELECT t.*, p.name AS project_name, u.display_name AS assignee_name
            FROM tickets t
            JOIN projects p ON p.id = t.project_id
            LEFT JOIN users u ON u.id = t.assignee_id
            ORDER BY
                CASE t.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END,
                t.updated_at DESC,
                t.id DESC
        """,
        "roles": {
            "GET": ALL_ROLES,
            "POST": ("admin", "manager", "staff"),
            "PUT": ("admin", "manager", "staff"),
            "DELETE": ("admin", "manager"),
        },
    },
}


def now():
    return int(time.time())


def cleanup_sessions():
    current = now()
    expired = [sid for sid, value in SESSIONS.items() if value["expires_at"] < current]
    for sid in expired:
        del SESSIONS[sid]


def audit(connection, actor_id, action, entity, entity_id=None, detail=""):
    connection.execute(
        """
        INSERT INTO audit_logs (actor_id, action, entity, entity_id, detail)
        VALUES (?, ?, ?, ?, ?)
        """,
        (actor_id, action, entity, entity_id, detail),
    )


def get_request_body(handler):
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length == 0:
        return {}
    raw = handler.rfile.read(content_length).decode("utf-8")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError("请求体必须是合法 JSON") from exc


def serialize_value(value):
    if value == "":
        return None
    return value


def validate_payload(payload, required_fields):
    missing = [field for field in required_fields if not payload.get(field)]
    if missing:
        return f"缺少必填字段: {', '.join(missing)}"
    return None


def make_handler(db_path):
    class EnterpriseRequestHandler(BaseHTTPRequestHandler):
        server_version = "EnterpriseFinalProject/1.0"

        def log_message(self, fmt, *args):
            return

        def do_GET(self):
            self.dispatch("GET")

        def do_POST(self):
            self.dispatch("POST")

        def do_PUT(self):
            self.dispatch("PUT")

        def do_DELETE(self):
            self.dispatch("DELETE")

        def dispatch(self, method):
            parsed = urlparse(self.path)
            path = parsed.path
            query = parse_qs(parsed.query)
            try:
                if path == "/" or path == "/index.html":
                    return self.serve_static("index.html")
                if path.startswith("/static/"):
                    return self.serve_static(path.removeprefix("/static/"))
                if path.startswith("/api/"):
                    return self.handle_api(method, path, query)
                self.send_json({"error": "资源不存在"}, HTTPStatus.NOT_FOUND)
            except ValueError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)
            except PermissionError as exc:
                self.send_json({"error": str(exc)}, HTTPStatus.FORBIDDEN)
            except Exception as exc:
                self.send_json({"error": f"服务器内部错误: {exc}"}, HTTPStatus.INTERNAL_SERVER_ERROR)

        def serve_static(self, relative_path):
            target = (STATIC_DIR / relative_path).resolve()
            try:
                target.relative_to(STATIC_DIR.resolve())
            except ValueError:
                return self.send_json({"error": "非法静态资源路径"}, HTTPStatus.BAD_REQUEST)
            if not target.is_file():
                return self.send_json({"error": "静态资源不存在"}, HTTPStatus.NOT_FOUND)

            body = target.read_bytes()
            content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def send_json(self, payload, status=HTTPStatus.OK, extra_headers=None):
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for key, value in (extra_headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            self.wfile.write(body)

        def current_user(self, connection):
            cleanup_sessions()
            cookie_header = self.headers.get("Cookie", "")
            cookie = SimpleCookie(cookie_header)
            morsel = cookie.get(SESSION_COOKIE)
            if morsel is None:
                return None
            session = SESSIONS.get(morsel.value)
            if session is None:
                return None
            user = connection.execute(
                """
                SELECT id, username, display_name, role, department, active, created_at
                FROM users
                WHERE id = ? AND active = 1
                """,
                (session["user_id"],),
            ).fetchone()
            return row_to_dict(user)

        def require_user(self, connection):
            user = self.current_user(connection)
            if user is None:
                self.send_json({"error": "请先登录"}, HTTPStatus.UNAUTHORIZED)
                return None
            return user

        def require_role(self, user, allowed_roles):
            if not can_access(user["role"], allowed_roles):
                raise PermissionError("当前角色无权执行该操作")

        def handle_api(self, method, path, query):
            segments = [segment for segment in path.split("/") if segment][1:]

            if segments == ["health"]:
                return self.send_json({"status": "ok"})

            with connect(db_path) as connection:
                if segments == ["login"] and method == "POST":
                    return self.handle_login(connection)

                user = self.require_user(connection)
                if user is None:
                    return

                if segments == ["logout"] and method == "POST":
                    return self.handle_logout()
                if segments == ["me"] and method == "GET":
                    user["role_label"] = ROLE_LABELS.get(user["role"], user["role"])
                    return self.send_json({"user": user})
                if segments == ["dashboard"] and method == "GET":
                    return self.handle_dashboard(connection)
                if segments == ["options"] and method == "GET":
                    return self.handle_options(connection)
                if segments == ["agent", "ask"] and method == "POST":
                    return self.handle_agent_ask(connection, user)
                if segments == ["agent", "stream"] and method == "GET":
                    return self.handle_agent_stream(connection, user, query)
                if segments == ["agent", "runs"] and method == "GET":
                    self.require_role(user, ("admin", "manager"))
                    return self.send_json({"items": list_runs(connection)})
                if len(segments) == 3 and segments[0] == "agent" and segments[1] == "runs" and method == "GET":
                    self.require_role(user, ("admin", "manager"))
                    return self.send_json({"items": list_steps(connection, int(segments[2]))})
                if segments == ["mcp", "tools"] and method == "GET":
                    return self.send_json({"tools": list_tools()})
                if segments == ["mcp", "call"] and method == "POST":
                    return self.handle_mcp_call(connection, user)
                if segments == ["approvals"] and method == "GET":
                    self.require_role(user, ALL_ROLES)
                    return self.handle_approvals(connection)
                if len(segments) == 3 and segments[0] == "approvals" and segments[2] == "decision" and method == "POST":
                    self.require_role(user, ("admin", "manager", "finance"))
                    return self.handle_approval_decision(connection, user, int(segments[1]))
                if segments == ["audit-logs"] and method == "GET":
                    self.require_role(user, ("admin", "manager", "finance"))
                    return self.handle_audit_logs(connection)
                if segments and segments[0] == "users":
                    return self.handle_users(connection, user, method, segments)
                if segments and segments[0] in RESOURCE_CONFIG:
                    return self.handle_resource(connection, user, method, segments)

            self.send_json({"error": "API 路由不存在"}, HTTPStatus.NOT_FOUND)

        def handle_login(self, connection):
            payload = get_request_body(self)
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", ""))
            user = connection.execute(
                """
                SELECT id, username, password_hash, display_name, role, department, active, created_at
                FROM users
                WHERE username = ?
                """,
                (username,),
            ).fetchone()
            if user is None or not user["active"] or not verify_password(password, user["password_hash"]):
                return self.send_json({"error": "用户名或密码错误"}, HTTPStatus.UNAUTHORIZED)

            session_id = secrets.token_urlsafe(32)
            SESSIONS[session_id] = {"user_id": user["id"], "expires_at": now() + SESSION_TTL_SECONDS}
            audit(connection, user["id"], "login", "session", None, "用户登录系统")
            connection.commit()

            public_user = row_to_dict(user)
            public_user.pop("password_hash", None)
            public_user["role_label"] = ROLE_LABELS.get(public_user["role"], public_user["role"])
            cookie = f"{SESSION_COOKIE}={session_id}; Path=/; HttpOnly; SameSite=Lax; Max-Age={SESSION_TTL_SECONDS}"
            return self.send_json({"user": public_user}, extra_headers={"Set-Cookie": cookie})

        def handle_logout(self):
            cookie_header = self.headers.get("Cookie", "")
            cookie = SimpleCookie(cookie_header)
            morsel = cookie.get(SESSION_COOKIE)
            if morsel is not None:
                SESSIONS.pop(morsel.value, None)
            expired = f"{SESSION_COOKIE}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
            return self.send_json({"ok": True}, extra_headers={"Set-Cookie": expired})

        def handle_dashboard(self, connection):
            metrics = {
                "customers": connection.execute("SELECT COUNT(*) AS value FROM customers").fetchone()["value"],
                "active_projects": connection.execute(
                    "SELECT COUNT(*) AS value FROM projects WHERE stage IN ('initiating', 'running', 'delivery')"
                ).fetchone()["value"],
                "contract_amount": connection.execute(
                    "SELECT COALESCE(SUM(amount), 0) AS value FROM contracts WHERE status IN ('active', 'pending')"
                ).fetchone()["value"],
                "open_tickets": connection.execute(
                    "SELECT COUNT(*) AS value FROM tickets WHERE status IN ('open', 'processing')"
                ).fetchone()["value"],
                "pending_approvals": connection.execute(
                    "SELECT COUNT(*) AS value FROM approvals WHERE status = 'pending'"
                ).fetchone()["value"],
            }
            pipeline = rows_to_list(
                connection.execute(
                    """
                    SELECT stage, COUNT(*) AS count, COALESCE(SUM(budget), 0) AS budget
                    FROM projects
                    GROUP BY stage
                    ORDER BY stage
                    """
                ).fetchall()
            )
            risk = rows_to_list(
                connection.execute(
                    """
                    SELECT risk_level, COUNT(*) AS count
                    FROM projects
                    GROUP BY risk_level
                    ORDER BY CASE risk_level WHEN 'high' THEN 1 WHEN 'middle' THEN 2 ELSE 3 END
                    """
                ).fetchall()
            )
            recent_tickets = rows_to_list(
                connection.execute(
                    """
                    SELECT t.id, t.title, t.priority, t.status, p.name AS project_name
                    FROM tickets t
                    JOIN projects p ON p.id = t.project_id
                    ORDER BY t.updated_at DESC
                    LIMIT 6
                    """
                ).fetchall()
            )
            return self.send_json({"metrics": metrics, "pipeline": pipeline, "risk": risk, "recent_tickets": recent_tickets})

        def handle_agent_ask(self, connection, user):
            payload = get_request_body(self)
            message = str(payload.get("message", "")).strip()
            if not message:
                return self.send_json({"error": "message 不能为空"}, HTTPStatus.BAD_REQUEST)
            result = EnterpriseAgent(connection, user).run(message)
            return self.send_json(result)

        def handle_agent_stream(self, connection, user, query):
            message = (query.get("message") or [""])[0].strip()
            if not message:
                return self.send_json({"error": "message 不能为空"}, HTTPStatus.BAD_REQUEST)

            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Connection", "keep-alive")
            self.end_headers()

            try:
                for event in EnterpriseAgent(connection, user).run_stream(message):
                    payload = json.dumps(event, ensure_ascii=False)
                    self.wfile.write(f"event: {event['type']}\n".encode("utf-8"))
                    self.wfile.write(f"data: {payload}\n\n".encode("utf-8"))
                    self.wfile.flush()
            except BrokenPipeError:
                return

        def handle_mcp_call(self, connection, user):
            payload = get_request_body(self)
            name = payload.get("name")
            arguments = payload.get("arguments", {})
            result = call_tool(name, arguments, connection, user)
            connection.commit()
            return self.send_json({"result": result})

        def handle_options(self, connection):
            return self.send_json(
                {
                    "customers": rows_to_list(connection.execute("SELECT id, name FROM customers ORDER BY name").fetchall()),
                    "projects": rows_to_list(connection.execute("SELECT id, name FROM projects ORDER BY name").fetchall()),
                    "users": rows_to_list(
                        connection.execute(
                            "SELECT id, username, display_name, role FROM users WHERE active = 1 ORDER BY role, display_name"
                        ).fetchall()
                    ),
                }
            )

        def handle_resource(self, connection, user, method, segments):
            resource = segments[0]
            config = RESOURCE_CONFIG[resource]
            self.require_role(user, config["roles"].get(method, ()))

            if len(segments) == 1 and method == "GET":
                return self.send_json({"items": rows_to_list(connection.execute(config["list_sql"]).fetchall())})

            if len(segments) == 1 and method == "POST":
                payload = get_request_body(self)
                error = validate_payload(payload, config["required"])
                if error:
                    return self.send_json({"error": error}, HTTPStatus.BAD_REQUEST)
                fields = [field for field in config["fields"] if field in payload]
                values = [serialize_value(payload.get(field)) for field in fields]
                placeholders = ", ".join("?" for _ in fields)
                cursor = connection.execute(
                    f"INSERT INTO {config['table']} ({', '.join(fields)}) VALUES ({placeholders})",
                    values,
                )
                entity_id = cursor.lastrowid
                if resource == "contracts":
                    connection.execute(
                        """
                        INSERT INTO approvals (target_type, target_id, applicant_id, status, comment)
                        VALUES ('contract', ?, ?, 'pending', '合同提交后自动生成审批记录')
                        """,
                        (entity_id, user["id"]),
                    )
                audit(connection, user["id"], "create", resource, entity_id, f"新增 {resource} 记录")
                connection.commit()
                return self.send_json({"id": entity_id}, HTTPStatus.CREATED)

            if len(segments) == 2 and method == "PUT":
                entity_id = int(segments[1])
                payload = get_request_body(self)
                fields = [field for field in config["fields"] if field in payload]
                if not fields:
                    return self.send_json({"error": "没有可更新字段"}, HTTPStatus.BAD_REQUEST)
                assignments = ", ".join(f"{field} = ?" for field in fields)
                values = [serialize_value(payload.get(field)) for field in fields] + [entity_id]
                connection.execute(f"UPDATE {config['table']} SET {assignments} WHERE id = ?", values)
                audit(connection, user["id"], "update", resource, entity_id, f"更新 {resource} 记录")
                connection.commit()
                return self.send_json({"ok": True})

            if len(segments) == 2 and method == "DELETE":
                entity_id = int(segments[1])
                connection.execute(f"DELETE FROM {config['table']} WHERE id = ?", (entity_id,))
                audit(connection, user["id"], "delete", resource, entity_id, f"删除 {resource} 记录")
                connection.commit()
                return self.send_json({"ok": True})

            return self.send_json({"error": "资源操作不存在"}, HTTPStatus.NOT_FOUND)

        def handle_users(self, connection, user, method, segments):
            self.require_role(user, ("admin",))
            if len(segments) == 1 and method == "GET":
                rows = connection.execute(
                    """
                    SELECT id, username, display_name, role, department, active, created_at
                    FROM users
                    ORDER BY active DESC, role, username
                    """
                ).fetchall()
                return self.send_json({"items": rows_to_list(rows)})

            payload = get_request_body(self) if method in ("POST", "PUT") else {}
            if len(segments) == 1 and method == "POST":
                for field in ("username", "password", "display_name", "role"):
                    if not payload.get(field):
                        return self.send_json({"error": f"缺少必填字段: {field}"}, HTTPStatus.BAD_REQUEST)
                cursor = connection.execute(
                    """
                    INSERT INTO users (username, password_hash, display_name, role, department, active)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        payload["username"],
                        hash_password(payload["password"]),
                        payload["display_name"],
                        payload["role"],
                        payload.get("department", ""),
                        int(payload.get("active", 1)),
                    ),
                )
                audit(connection, user["id"], "create", "users", cursor.lastrowid, "新增系统用户")
                connection.commit()
                return self.send_json({"id": cursor.lastrowid}, HTTPStatus.CREATED)

            if len(segments) == 2 and method == "PUT":
                entity_id = int(segments[1])
                allowed = ["username", "display_name", "role", "department", "active"]
                fields = [field for field in allowed if field in payload]
                values = [payload[field] for field in fields]
                if payload.get("password"):
                    fields.append("password_hash")
                    values.append(hash_password(payload["password"]))
                if not fields:
                    return self.send_json({"error": "没有可更新字段"}, HTTPStatus.BAD_REQUEST)
                assignments = ", ".join(f"{field} = ?" for field in fields)
                connection.execute(f"UPDATE users SET {assignments} WHERE id = ?", values + [entity_id])
                audit(connection, user["id"], "update", "users", entity_id, "更新系统用户")
                connection.commit()
                return self.send_json({"ok": True})

            return self.send_json({"error": "用户操作不存在"}, HTTPStatus.NOT_FOUND)

        def handle_approvals(self, connection):
            rows = connection.execute(
                """
                SELECT
                    a.*,
                    applicant.display_name AS applicant_name,
                    reviewer.display_name AS reviewer_name,
                    ct.contract_no AS target_name,
                    ct.amount AS target_amount
                FROM approvals a
                LEFT JOIN users applicant ON applicant.id = a.applicant_id
                LEFT JOIN users reviewer ON reviewer.id = a.reviewer_id
                LEFT JOIN contracts ct ON a.target_type = 'contract' AND ct.id = a.target_id
                ORDER BY
                    CASE a.status WHEN 'pending' THEN 1 ELSE 2 END,
                    a.created_at DESC
                """
            ).fetchall()
            return self.send_json({"items": rows_to_list(rows)})

        def handle_approval_decision(self, connection, user, approval_id):
            payload = get_request_body(self)
            decision = payload.get("decision")
            comment = str(payload.get("comment", "")).strip()
            if decision not in ("approved", "rejected"):
                return self.send_json({"error": "审批结果必须是 approved 或 rejected"}, HTTPStatus.BAD_REQUEST)
            approval = connection.execute("SELECT * FROM approvals WHERE id = ?", (approval_id,)).fetchone()
            if approval is None:
                return self.send_json({"error": "审批记录不存在"}, HTTPStatus.NOT_FOUND)
            if approval["status"] != "pending":
                return self.send_json({"error": "该审批已经处理"}, HTTPStatus.BAD_REQUEST)
            connection.execute(
                """
                UPDATE approvals
                SET status = ?, reviewer_id = ?, comment = ?, reviewed_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (decision, user["id"], comment or ("审批通过" if decision == "approved" else "审批驳回"), approval_id),
            )
            if approval["target_type"] == "contract":
                new_status = "active" if decision == "approved" else "rejected"
                connection.execute("UPDATE contracts SET status = ? WHERE id = ?", (new_status, approval["target_id"]))
            audit(connection, user["id"], decision, "approvals", approval_id, comment)
            connection.commit()
            return self.send_json({"ok": True})

        def handle_audit_logs(self, connection):
            rows = connection.execute(
                """
                SELECT l.*, u.display_name AS actor_name, u.username AS actor_username
                FROM audit_logs l
                LEFT JOIN users u ON u.id = l.actor_id
                ORDER BY l.created_at DESC, l.id DESC
                LIMIT 120
                """
            ).fetchall()
            return self.send_json({"items": rows_to_list(rows)})

    return EnterpriseRequestHandler


def create_server(host="127.0.0.1", port=8000, db_path=None):
    database_path = initialize_database(db_path or DEFAULT_DB_PATH)
    handler = make_handler(database_path)
    return ThreadingHTTPServer((host, port), handler)


def main():
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8000"))
    server = create_server(host=host, port=port)
    host, port = server.server_address
    print(f"Enterprise final project is running at http://{host}:{port}")
    print("Default accounts: admin/123456, manager/123456, finance/123456, staff/123456")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
