import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BENCHMARK_DB = ROOT / "data" / "benchmark_agent.db"

import sys

sys.path.insert(0, str(ROOT))

from app.agent.agent import EnterpriseAgent  # noqa: E402
from app.database import connect, initialize_database  # noqa: E402


def run_case(connection, case):
    user = {"id": 1, "username": "admin", "display_name": "系统管理员", "role": "admin"}
    result = EnterpriseAgent(connection, user).run(case["prompt"])
    actual_tools = [step["tool_name"] for step in result["steps"]]
    answer = result["answer"]
    tool_score = sum(1 for tool in case["expected_tools"] if tool in actual_tools) / len(case["expected_tools"])
    keyword_score = sum(1 for word in case["expected_keywords"] if word in answer) / len(case["expected_keywords"])
    return {
        "id": case["id"],
        "prompt": case["prompt"],
        "actual_tools": actual_tools,
        "tool_score": round(tool_score, 2),
        "keyword_score": round(keyword_score, 2),
        "passed": tool_score >= 0.8 and keyword_score >= 0.5,
    }


def main():
    cases = json.loads((ROOT / "eval" / "benchmark_cases.json").read_text(encoding="utf-8"))
    BENCHMARK_DB.parent.mkdir(exist_ok=True)
    if BENCHMARK_DB.exists():
        BENCHMARK_DB.unlink()
    initialize_database(BENCHMARK_DB)
    with connect(BENCHMARK_DB) as connection:
        results = [run_case(connection, case) for case in cases]
        passed = sum(1 for item in results if item["passed"])
        print(json.dumps({"passed": passed, "total": len(results), "results": results}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
