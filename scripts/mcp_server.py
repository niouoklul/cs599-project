import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.agent.tools import call_tool, list_tools  # noqa: E402
from app.database import connect, initialize_database  # noqa: E402


def write_response(response):
    sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def main():
    initialize_database()
    user = {"id": 1, "username": "mcp", "role": "admin", "display_name": "MCP Client"}
    for line in sys.stdin:
        if not line.strip():
            continue
        request = json.loads(line)
        method = request.get("method")
        request_id = request.get("id")
        try:
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "cs599-enterprise-agent", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                }
            elif method == "tools/list":
                result = {"tools": list_tools()}
            elif method == "tools/call":
                params = request.get("params", {})
                with connect() as connection:
                    observation = call_tool(params.get("name"), params.get("arguments", {}), connection, user)
                    connection.commit()
                result = {"content": [{"type": "text", "text": json.dumps(observation, ensure_ascii=False)}]}
            else:
                raise ValueError(f"Unsupported method: {method}")
            write_response({"jsonrpc": "2.0", "id": request_id, "result": result})
        except Exception as exc:
            write_response({"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": str(exc)}})


if __name__ == "__main__":
    main()
