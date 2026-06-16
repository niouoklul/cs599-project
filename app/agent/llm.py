import json
import os
import urllib.error
import urllib.request

from .tools import list_tools


class DeepSeekPlanner:
    """Planner backed by free or official DeepSeek-compatible Tool Calls APIs."""

    def __init__(self):
        self.provider_name, self.api_key, self.base_url, self.model = self._select_provider()
        self.timeout = float(
            os.environ.get("FREE_DEEPSEEK_TIMEOUT")
            or os.environ.get("DEEPSEEK_TIMEOUT")
            or os.environ.get("AGENT_TIMEOUT", "12")
        )

    def _select_provider(self):
        free_key = os.environ.get("FREE_DEEPSEEK_API_KEY") or os.environ.get("SILICONFLOW_API_KEY")
        if free_key:
            return (
                "free-deepseek-api",
                free_key,
                os.environ.get("FREE_DEEPSEEK_BASE_URL")
                or os.environ.get("SILICONFLOW_BASE_URL")
                or "https://api.siliconflow.cn/v1",
                os.environ.get("FREE_DEEPSEEK_MODEL")
                or os.environ.get("SILICONFLOW_MODEL")
                or os.environ.get("AGENT_MODEL")
                or "deepseek-ai/DeepSeek-V3.2",
            )

        official_key = os.environ.get("DEEPSEEK_API_KEY")
        if official_key:
            return (
                "deepseek-official-api",
                official_key,
                os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
                os.environ.get("DEEPSEEK_MODEL") or os.environ.get("AGENT_MODEL") or "deepseek-v4-pro",
            )

        return (
            "deepseek-api",
            "",
            os.environ.get("FREE_DEEPSEEK_BASE_URL") or "https://api.siliconflow.cn/v1",
            os.environ.get("FREE_DEEPSEEK_MODEL") or os.environ.get("AGENT_MODEL") or "deepseek-ai/DeepSeek-V3.2",
        )

    @property
    def available(self):
        return bool(self.api_key)

    @property
    def endpoint(self):
        base = self.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return base + "/chat/completions"

    def plan(self, message, memory):
        if not self.available:
            raise RuntimeError("FREE_DEEPSEEK_API_KEY/SILICONFLOW_API_KEY or DEEPSEEK_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "你是企业项目协同系统的 Agent 工具规划器。"
                        "请根据用户目标选择一个或多个工具调用。"
                        "只能使用 tools 中提供的工具，不要编造工具名。"
                        "如果任务涉及写操作，只调用最小必要工具。"
                        "如果需要先查规则或业务数据，可以先调用检索/查询类工具。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "message": message,
                            "recent_memory": memory[-4:],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            "tools": self._tools_schema(),
            "tool_choice": "auto",
            "temperature": 0.1,
            "max_tokens": 512,
            "stream": False,
        }
        request = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")[:300]
            raise RuntimeError(f"{self.provider_name} planner failed: HTTP {exc.code}: {body}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"{self.provider_name} planner failed: {exc}") from exc

        message_obj = data["choices"][0].get("message", {})
        plan = self._parse_tool_calls(message_obj.get("tool_calls") or [])
        if not plan:
            plan = self._parse_json_fallback(message_obj.get("content") or "")
        if not plan:
            raise RuntimeError(f"{self.provider_name} returned no valid tool calls")
        return plan

    def _tools_schema(self):
        tools = []
        for tool in list_tools():
            tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                    },
                }
            )
        return tools

    def _parse_tool_calls(self, tool_calls):
        valid_names = {tool["name"] for tool in list_tools()}
        plan = []
        for call in tool_calls:
            function = call.get("function", {})
            tool_name = function.get("name")
            if tool_name not in valid_names:
                continue
            raw_args = function.get("arguments") or "{}"
            try:
                tool_args = json.loads(raw_args) if isinstance(raw_args, str) else raw_args
            except json.JSONDecodeError:
                tool_args = {}
            plan.append((f"DeepSeek 调用工具 {tool_name}", tool_name, tool_args or {}))
        return plan

    def _parse_json_fallback(self, content):
        if not content.strip():
            return []
        content = self._extract_json(content)
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            return []
        calls = parsed if isinstance(parsed, list) else parsed.get("calls", [])
        valid_names = {tool["name"] for tool in list_tools()}
        plan = []
        for call in calls:
            tool_name = call.get("tool_name")
            if tool_name in valid_names:
                plan.append(
                    (
                        call.get("thought") or f"DeepSeek 调用工具 {tool_name}",
                        tool_name,
                        call.get("tool_args") or {},
                    )
                )
        return plan

    def _extract_json(self, content):
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return content[start : end + 1]
        return content
