from datetime import date


TOOL_DEFINITIONS = [
    {
        "name": "get_dashboard_metrics",
        "description": "读取经营看板指标，包括客户、活跃项目、合同金额、未关闭工单和待审批数量。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "search_projects",
        "description": "按关键字、阶段或风险等级查询项目。",
        "input_schema": {
            "type": "object",
            "properties": {
                "keyword": {"type": "string"},
                "stage": {"type": "string"},
                "risk_level": {"type": "string"},
            },
        },
    },
    {
        "name": "search_tickets",
        "description": "查询工单，可按状态、优先级或项目名称过滤。",
        "input_schema": {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "priority": {"type": "string"},
                "project_keyword": {"type": "string"},
            },
        },
    },
    {
        "name": "create_ticket",
        "description": "为指定项目创建一条工单。",
        "input_schema": {
            "type": "object",
            "properties": {
                "project_keyword": {"type": "string"},
                "title": {"type": "string"},
                "priority": {"type": "string"},
                "description": {"type": "string"},
                "assignee_keyword": {"type": "string"},
            },
            "required": ["project_keyword", "title"],
        },
    },
    {
        "name": "route_ticket",
        "description": "按负载和优先级自动分派工单。",
        "input_schema": {
            "type": "object",
            "properties": {"ticket_id": {"type": "integer"}},
            "required": ["ticket_id"],
        },
    },
    {
        "name": "analyze_project_risks",
        "description": "分析项目风险，合并风险等级、紧急工单、待审批合同和交付日期。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "generate_weekly_report",
        "description": "生成企业经营周报，适合 Demo 和答辩展示。",
        "input_schema": {"type": "object", "properties": {}},
    },
    {
        "name": "approve_contract",
        "description": "根据合同编号审批或驳回合同。",
        "input_schema": {
            "type": "object",
            "properties": {
                "contract_no": {"type": "string"},
                "decision": {"type": "string", "enum": ["approved", "rejected"]},
                "comment": {"type": "string"},
            },
            "required": ["contract_no", "decision"],
        },
    },
    {
        "name": "search_knowledge",
        "description": "从企业知识库检索流程、审批、风险和周报规则。",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    },
]


def list_tools():
    return TOOL_DEFINITIONS


def call_tool(name, arguments, connection, user):
    arguments = arguments or {}
    if name == "get_dashboard_metrics":
        return get_dashboard_metrics(connection)
    if name == "search_projects":
        return search_projects(connection, **arguments)
    if name == "search_tickets":
        return search_tickets(connection, **arguments)
    if name == "create_ticket":
        return create_ticket(connection, user, **arguments)
    if name == "route_ticket":
        return route_ticket(connection, user, **arguments)
    if name == "analyze_project_risks":
        return analyze_project_risks(connection)
    if name == "generate_weekly_report":
        return generate_weekly_report(connection)
    if name == "approve_contract":
        return approve_contract(connection, user, **arguments)
    if name == "search_knowledge":
        return search_knowledge(connection, **arguments)
    raise ValueError(f"Unknown tool: {name}")


def _audit(connection, user_id, action, entity, entity_id=None, detail=""):
    connection.execute(
        """
        INSERT INTO audit_logs (actor_id, action, entity, entity_id, detail)
        VALUES (?, ?, ?, ?, ?)
        """,
        (user_id, action, entity, entity_id, detail),
    )


def get_dashboard_metrics(connection):
    metrics = {
        "customers": connection.execute("SELECT COUNT(*) AS value FROM customers").fetchone()["value"],
        "active_projects": connection.execute(
            "SELECT COUNT(*) AS value FROM projects WHERE stage IN ('initiating','running','delivery')"
        ).fetchone()["value"],
        "contract_amount": connection.execute(
            "SELECT COALESCE(SUM(amount), 0) AS value FROM contracts WHERE status IN ('active','pending')"
        ).fetchone()["value"],
        "open_tickets": connection.execute(
            "SELECT COUNT(*) AS value FROM tickets WHERE status IN ('open','processing')"
        ).fetchone()["value"],
        "pending_approvals": connection.execute(
            "SELECT COUNT(*) AS value FROM approvals WHERE status = 'pending'"
        ).fetchone()["value"],
    }
    return {"metrics": metrics}


def search_projects(connection, keyword="", stage="", risk_level=""):
    sql = """
        SELECT p.id, p.name, p.stage, p.budget, p.start_date, p.end_date, p.risk_level,
               c.name AS customer_name, u.display_name AS owner_name
        FROM projects p
        JOIN customers c ON c.id = p.customer_id
        LEFT JOIN users u ON u.id = p.owner_id
        WHERE 1 = 1
    """
    params = []
    if keyword:
        sql += " AND (p.name LIKE ? OR c.name LIKE ?)"
        params.extend([f"%{keyword}%", f"%{keyword}%"])
    if stage:
        sql += " AND p.stage = ?"
        params.append(stage)
    if risk_level:
        sql += " AND p.risk_level = ?"
        params.append(risk_level)
    sql += " ORDER BY CASE p.risk_level WHEN 'high' THEN 1 WHEN 'middle' THEN 2 ELSE 3 END, p.end_date"
    return {"projects": [dict(row) for row in connection.execute(sql, params).fetchall()]}


def search_tickets(connection, status="", priority="", project_keyword=""):
    sql = """
        SELECT t.id, t.title, t.priority, t.status, t.description,
               p.name AS project_name, u.display_name AS assignee_name
        FROM tickets t
        JOIN projects p ON p.id = t.project_id
        LEFT JOIN users u ON u.id = t.assignee_id
        WHERE 1 = 1
    """
    params = []
    if status:
        sql += " AND t.status = ?"
        params.append(status)
    if priority:
        sql += " AND t.priority = ?"
        params.append(priority)
    if project_keyword:
        sql += " AND p.name LIKE ?"
        params.append(f"%{project_keyword}%")
    sql += " ORDER BY CASE t.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'normal' THEN 3 ELSE 4 END, t.id DESC"
    return {"tickets": [dict(row) for row in connection.execute(sql, params).fetchall()]}


def create_ticket(connection, user, project_keyword, title, priority="normal", description="", assignee_keyword=""):
    project = connection.execute(
        "SELECT id, name FROM projects WHERE name LIKE ? ORDER BY id LIMIT 1",
        (f"%{project_keyword}%",),
    ).fetchone()
    if project is None:
        return {"error": "未找到匹配项目", "project_keyword": project_keyword}

    assignee = None
    if assignee_keyword:
        assignee = connection.execute(
            """
            SELECT id, display_name
            FROM users
            WHERE active = 1 AND (display_name LIKE ? OR username LIKE ?)
            ORDER BY id LIMIT 1
            """,
            (f"%{assignee_keyword}%", f"%{assignee_keyword}%"),
        ).fetchone()

    cursor = connection.execute(
        """
        INSERT INTO tickets (project_id, title, priority, status, assignee_id, description)
        VALUES (?, ?, ?, 'open', ?, ?)
        """,
        (project["id"], title, priority or "normal", assignee["id"] if assignee else None, description or ""),
    )
    _audit(connection, user["id"], "agent_create_ticket", "tickets", cursor.lastrowid, title)
    return {"ticket_id": cursor.lastrowid, "project": project["name"], "assignee": assignee["display_name"] if assignee else "未分派"}


def route_ticket(connection, user, ticket_id):
    ticket = connection.execute(
        """
        SELECT t.id, t.title, t.priority, t.status, p.owner_id
        FROM tickets t
        JOIN projects p ON p.id = t.project_id
        WHERE t.id = ?
        """,
        (ticket_id,),
    ).fetchone()
    if ticket is None:
        return {"error": "工单不存在", "ticket_id": ticket_id}

    assignee = connection.execute(
        """
        SELECT u.id, u.display_name, COUNT(open_t.id) AS open_count
        FROM users u
        LEFT JOIN tickets open_t
            ON open_t.assignee_id = u.id AND open_t.status IN ('open','processing')
        WHERE u.active = 1 AND u.role IN ('staff', 'manager')
        GROUP BY u.id
        ORDER BY
            CASE WHEN u.id = ? THEN 0 ELSE 1 END,
            open_count ASC,
            u.id ASC
        LIMIT 1
        """,
        (ticket["owner_id"] if ticket["priority"] != "urgent" else -1,),
    ).fetchone()
    if assignee is None:
        return {"error": "没有可用处理人"}

    connection.execute(
        "UPDATE tickets SET assignee_id = ?, status = 'processing' WHERE id = ?",
        (assignee["id"], ticket_id),
    )
    _audit(connection, user["id"], "agent_route_ticket", "tickets", ticket_id, f"分派给 {assignee['display_name']}")
    return {
        "ticket_id": ticket_id,
        "title": ticket["title"],
        "assignee": assignee["display_name"],
        "reason": "按项目负责人优先和当前未关闭工单负载选择处理人",
    }


def analyze_project_risks(connection):
    projects = connection.execute(
        """
        SELECT p.id, p.name, p.risk_level, p.end_date, c.name AS customer_name
        FROM projects p
        JOIN customers c ON c.id = p.customer_id
        ORDER BY p.id
        """
    ).fetchall()
    today = date.today().isoformat()
    risks = []
    for project in projects:
        open_ticket_count = connection.execute(
            """
            SELECT COUNT(*) AS value
            FROM tickets
            WHERE project_id = ? AND status IN ('open','processing')
            """,
            (project["id"],),
        ).fetchone()["value"]
        urgent_ticket_count = connection.execute(
            """
            SELECT COUNT(*) AS value
            FROM tickets
            WHERE project_id = ? AND status IN ('open','processing') AND priority = 'urgent'
            """,
            (project["id"],),
        ).fetchone()["value"]
        pending_contracts = connection.execute(
            """
            SELECT COUNT(*) AS value
            FROM contracts
            WHERE project_id = ? AND status = 'pending'
            """,
            (project["id"],),
        ).fetchone()["value"]
        score = 0
        reasons = []
        if project["risk_level"] == "high":
            score += 40
            reasons.append("项目自身标记为高风险")
        elif project["risk_level"] == "middle":
            score += 20
            reasons.append("项目风险等级为中")
        if urgent_ticket_count:
            score += 30
            reasons.append(f"存在 {urgent_ticket_count} 个紧急未关闭工单")
        if open_ticket_count >= 2:
            score += 15
            reasons.append(f"未关闭工单数量为 {open_ticket_count}")
        if pending_contracts:
            score += 15
            reasons.append(f"存在 {pending_contracts} 个待审批合同")
        if project["end_date"] and project["end_date"] < today:
            score += 20
            reasons.append("项目计划结束日期已过")
        if score > 0:
            risks.append(
                {
                    "project_id": project["id"],
                    "project_name": project["name"],
                    "customer_name": project["customer_name"],
                    "score": min(score, 100),
                    "reasons": reasons,
                }
            )
    risks.sort(key=lambda item: item["score"], reverse=True)
    return {"risks": risks}


def generate_weekly_report(connection):
    metrics = get_dashboard_metrics(connection)["metrics"]
    risks = analyze_project_risks(connection)["risks"][:3]
    pending = connection.execute(
        """
        SELECT ct.contract_no, ct.amount, p.name AS project_name
        FROM approvals a
        JOIN contracts ct ON ct.id = a.target_id AND a.target_type = 'contract'
        JOIN projects p ON p.id = ct.project_id
        WHERE a.status = 'pending'
        ORDER BY a.created_at DESC
        """
    ).fetchall()
    lines = [
        "### 企业项目协同系统经营周报",
        f"- 客户总数：{metrics['customers']} 个",
        f"- 活跃项目：{metrics['active_projects']} 个",
        f"- 在管合同金额：{metrics['contract_amount']:.2f} 元",
        f"- 未关闭工单：{metrics['open_tickets']} 个",
        f"- 待审批事项：{metrics['pending_approvals']} 个",
        "",
        "#### 风险提醒",
    ]
    if risks:
        for risk in risks:
            lines.append(f"- {risk['project_name']}（{risk['score']} 分）：{'；'.join(risk['reasons'])}")
    else:
        lines.append("- 暂无显著项目风险。")
    lines.append("")
    lines.append("#### 待办建议")
    if pending:
        for item in pending:
            lines.append(f"- 复核合同 {item['contract_no']}，项目：{item['project_name']}，金额：{item['amount']:.2f} 元。")
    else:
        lines.append("- 本周暂无待审批合同。")
    lines.append("- 优先关闭紧急工单，并对高风险项目进行项目经理复盘。")
    return {"report": "\n".join(lines)}


def approve_contract(connection, user, contract_no, decision, comment=""):
    if user["role"] not in ("admin", "manager", "finance"):
        return {"error": "当前角色无权审批合同"}
    contract = connection.execute(
        "SELECT id, status FROM contracts WHERE contract_no = ?",
        (contract_no,),
    ).fetchone()
    if contract is None:
        return {"error": "未找到合同", "contract_no": contract_no}
    if decision not in ("approved", "rejected"):
        return {"error": "decision 必须为 approved 或 rejected"}
    new_status = "active" if decision == "approved" else "rejected"
    connection.execute("UPDATE contracts SET status = ? WHERE id = ?", (new_status, contract["id"]))
    connection.execute(
        """
        UPDATE approvals
        SET status = ?, reviewer_id = ?, comment = ?, reviewed_at = CURRENT_TIMESTAMP
        WHERE target_type = 'contract' AND target_id = ? AND status = 'pending'
        """,
        (decision, user["id"], comment or ("Agent 审批通过" if decision == "approved" else "Agent 审批驳回"), contract["id"]),
    )
    _audit(connection, user["id"], f"agent_{decision}_contract", "contracts", contract["id"], contract_no)
    return {"contract_no": contract_no, "status": new_status}


def search_knowledge(connection, query):
    tokens = [token for token in query.replace("，", " ").replace("。", " ").split() if token]
    rows = connection.execute("SELECT id, title, category, content FROM knowledge_base").fetchall()
    scored = []
    for row in rows:
        haystack = f"{row['title']} {row['category']} {row['content']}"
        score = sum(2 if token in row["title"] else 1 for token in tokens if token in haystack)
        if score or not tokens:
            scored.append((score, dict(row)))
    scored.sort(key=lambda item: item[0], reverse=True)
    return {"documents": [item for _, item in scored[:3]]}
