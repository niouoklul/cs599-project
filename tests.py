import http.cookiejar
import json
import os
import threading
import urllib.request
from pathlib import Path

from app.agent.agent import EnterpriseAgent
from app.database import connect, initialize_database
from app.security import hash_password, verify_password
from app.server import create_server


ROOT = Path(__file__).resolve().parent


def assert_true(condition, message):
    if not condition:
        raise AssertionError(message)


def test_password_hashing():
    stored = hash_password("123456")
    assert_true(verify_password("123456", stored), "password should verify")
    assert_true(not verify_password("bad", stored), "wrong password should fail")


def test_agent_tools(db_path):
    initialize_database(db_path)
    with connect(db_path) as connection:
        user = {"id": 1, "username": "admin", "display_name": "系统管理员", "role": "admin"}
        result = EnterpriseAgent(connection, user).run("分析当前高风险项目并给出预警")
        tools = [step["tool_name"] for step in result["steps"]]
        assert_true("analyze_project_risks" in tools, "agent should call risk tool")
        assert_true("风险" in result["answer"], "answer should mention risk")


def test_http_api(db_path):
    server = create_server("127.0.0.1", 0, db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://{server.server_address[0]}:{server.server_address[1]}"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def post(path, payload):
        request = urllib.request.Request(
            base + path,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(request, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    def get(path):
        with opener.open(base + path, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        login = post("/api/login", {"username": "admin", "password": "123456"})
        assert_true(login["user"]["role"] == "admin", "admin should login")
        dashboard = get("/api/dashboard")
        assert_true(dashboard["metrics"]["customers"] >= 1, "dashboard should load")
        answer = post("/api/agent/ask", {"message": "生成本周企业经营周报"})
        assert_true("generate_weekly_report" in [step["tool_name"] for step in answer["steps"]], "weekly report tool should run")
        assert_true("经营周报" in answer["answer"], "weekly report should be returned")
    finally:
        server.shutdown()
        server.server_close()


def main():
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    agent_db = data_dir / f"test_agent_tools_{os.getpid()}.db"
    http_db = data_dir / f"test_http_api_{os.getpid()}.db"
    test_password_hashing()
    test_agent_tools(agent_db)
    test_http_api(http_db)
    print("All tests passed.")


if __name__ == "__main__":
    main()
