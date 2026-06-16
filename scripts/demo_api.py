import http.cookiejar
import json
import sys
import urllib.request


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"


def main():
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def post(path, payload):
        request = urllib.request.Request(
            BASE_URL + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with opener.open(request, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    def get(path):
        with opener.open(BASE_URL + path, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    print("Login admin/123456")
    print(json.dumps(post("/api/login", {"username": "admin", "password": "123456"}), ensure_ascii=False, indent=2))

    print("\nDashboard")
    print(json.dumps(get("/api/dashboard")["metrics"], ensure_ascii=False, indent=2))

    prompts = [
        "生成本周企业经营周报",
        "分析当前高风险项目并给出预警",
        "请把 4 号紧急工单自动派单",
        "通过合同 HT-2026-003",
    ]
    for prompt in prompts:
        print(f"\nAgent prompt: {prompt}")
        result = post("/api/agent/ask", {"message": prompt})
        print("tools:", [step["tool_name"] for step in result["steps"]])
        print(result["answer"])


if __name__ == "__main__":
    main()
