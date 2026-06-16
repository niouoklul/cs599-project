import http.cookiejar
import json
import os
import sys
import threading
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.server import create_server  # noqa: E402


def request_json(opener, method, url, payload=None):
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method=method,
    )
    with opener.open(request, timeout=10) as response:
        return json.loads(response.read().decode("utf-8"))


def request_text(opener, url):
    with opener.open(url, timeout=10) as response:
        return response.read().decode("utf-8")


def main():
    data_dir = ROOT / "data"
    data_dir.mkdir(exist_ok=True)
    db_path = data_dir / f"smoke_web_{os.getpid()}.db"
    if db_path.exists():
        db_path.unlink()
    server = create_server("127.0.0.1", 0, db_path)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base_url = f"http://{server.server_address[0]}:{server.server_address[1]}"
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    try:
        index = request_text(opener, base_url + "/")
        assert "企业项目协同 Agent" in index
        login = request_json(opener, "POST", base_url + "/api/login", {"username": "admin", "password": "123456"})
        assert login["user"]["role"] == "admin"
        dashboard = request_json(opener, "GET", base_url + "/api/dashboard")
        assert dashboard["metrics"]["customers"] >= 1
        agent = request_json(opener, "POST", base_url + "/api/agent/ask", {"message": "生成本周企业经营周报"})
        assert agent["planner"]
        assert "经营周报" in agent["answer"]
        tools = [step["tool_name"] for step in agent["steps"]]
        assert "generate_weekly_report" in tools
        print(
            json.dumps(
                {
                    "status": "ok",
                    "base_url": base_url,
                    "planner": agent["planner"],
                    "tools": tools,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


if __name__ == "__main__":
    main()
