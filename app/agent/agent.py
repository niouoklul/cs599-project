import os

from .llm import DeepSeekPlanner
from .memory import create_run, finish_run, load_recent_memory, record_step, remember
from .tools import call_tool, list_tools
from .utils import contains_any, parse_contract_no, parse_first_int


class RuleBasedPlanner:
    """A deterministic fallback planner used when no external LLM key is configured."""

    def plan(self, message, memory):
        calls = []
        text = message or ""

        if contains_any(text, ["周报", "报告", "汇总", "经营"]):
            calls.extend(
                [
                    ("读取经营指标", "get_dashboard_metrics", {}),
                    ("识别项目风险", "analyze_project_risks", {}),
                    ("生成周报正文", "generate_weekly_report", {}),
                ]
            )
        elif contains_any(text, ["风险", "预警", "延期", "阻塞"]):
            calls.extend(
                [
                    ("检索风险规则", "search_knowledge", {"query": "项目风险 高风险 工单 合同"}),
                    ("分析项目风险", "analyze_project_risks", {}),
                ]
            )
        elif contains_any(text, ["派单", "分派", "指派", "路由"]):
            ticket_id = parse_first_int(text)
            if ticket_id is not None:
                calls.append(("按负载自动分派工单", "route_ticket", {"ticket_id": ticket_id}))
            else:
                calls.append(("先查看未关闭工单", "search_tickets", {"status": "open"}))
        elif contains_any(text, ["工单", "问题", "缺陷"]):
            priority = "urgent" if contains_any(text, ["紧急", "urgent"]) else ""
            calls.append(("查询相关工单", "search_tickets", {"priority": priority}))
        elif contains_any(text, ["合同", "审批", "通过", "驳回"]):
            contract_no = parse_contract_no(text)
            if contract_no and contains_any(text, ["通过", "批准", "同意"]):
                calls.append(("审批通过合同", "approve_contract", {"contract_no": contract_no, "decision": "approved"}))
            elif contract_no and contains_any(text, ["驳回", "拒绝"]):
                calls.append(("驳回合同", "approve_contract", {"contract_no": contract_no, "decision": "rejected"}))
            else:
                calls.append(("检索合同审批规则", "search_knowledge", {"query": "合同审批规则"}))
        elif contains_any(text, ["客户", "项目"]):
            risk_level = "high" if contains_any(text, ["高风险"]) else ""
            calls.append(("查询项目台账", "search_projects", {"keyword": "", "risk_level": risk_level}))
        else:
            calls.extend(
                [
                    ("检索企业知识库", "search_knowledge", {"query": text[:60]}),
                    ("读取经营指标", "get_dashboard_metrics", {}),
                ]
            )

        return calls


class EnterpriseAgent:
    def __init__(self, connection, user):
        self.connection = connection
        self.user = user
        self.fallback_planner = RuleBasedPlanner()
        self.deepseek_planner = DeepSeekPlanner()

    def run(self, message):
        events = list(self.run_stream(message))
        final_event = next(event for event in reversed(events) if event["type"] == "final")
        plan_event = next(event for event in events if event["type"] == "plan")
        return {
            "run_id": final_event["run_id"],
            "answer": final_event["answer"],
            "planner": plan_event.get("planner", "unknown"),
            "steps": [event for event in events if event["type"] == "tool_result"],
            "tools": list_tools(),
        }

    def run_stream(self, message):
        memory = load_recent_memory(self.connection, self.user["id"])
        run_id = create_run(self.connection, self.user["id"], message)
        remember(self.connection, self.user["id"], "user", message)
        planner_name = "local-rule"
        try:
            if self.deepseek_planner.available and os.environ.get("AGENT_DISABLE_LLM", "0") != "1":
                plan = self.deepseek_planner.plan(message, memory)
                planner_name = f"{self.deepseek_planner.provider_name}:{self.deepseek_planner.model}"
            else:
                plan = self.fallback_planner.plan(message, memory)
        except RuntimeError as exc:
            plan = self.fallback_planner.plan(message, memory)
            planner_name = f"local-rule fallback ({exc})"
        yield {
            "type": "plan",
            "run_id": run_id,
            "message": "已生成执行计划",
            "planner": planner_name,
            "plan": [item[1] for item in plan],
        }

        observations = []
        for index, (thought, tool_name, tool_args) in enumerate(plan, start=1):
            yield {
                "type": "tool_start",
                "run_id": run_id,
                "step_index": index,
                "thought": thought,
                "tool_name": tool_name,
                "tool_args": tool_args,
            }
            observation = call_tool(tool_name, tool_args, self.connection, self.user)
            record_step(self.connection, run_id, index, thought, tool_name, tool_args, observation)
            observations.append({"thought": thought, "tool_name": tool_name, "observation": observation})
            yield {
                "type": "tool_result",
                "run_id": run_id,
                "step_index": index,
                "thought": thought,
                "tool_name": tool_name,
                "tool_args": tool_args,
                "observation": observation,
            }

        answer = self.compose_answer(message, observations)
        remember(self.connection, self.user["id"], "assistant", answer)
        finish_run(self.connection, run_id, answer)
        self.connection.commit()
        yield {"type": "final", "run_id": run_id, "answer": answer}

    def compose_answer(self, message, observations):
        if not observations:
            return "我没有找到可执行的工具步骤，请换一种方式描述需求。"

        for item in observations:
            observation = item["observation"]
            if "report" in observation:
                return observation["report"]

        lines = ["我已完成本次 Agent 工具调用，结果如下："]
        for item in observations:
            tool = item["tool_name"]
            observation = item["observation"]
            if "error" in observation:
                lines.append(f"- {tool}: {observation['error']}")
            elif "metrics" in observation:
                metrics = observation["metrics"]
                lines.append(
                    f"- 经营指标：客户 {metrics['customers']} 个，活跃项目 {metrics['active_projects']} 个，"
                    f"未关闭工单 {metrics['open_tickets']} 个，待审批 {metrics['pending_approvals']} 个。"
                )
            elif "risks" in observation:
                risks = observation["risks"]
                if risks:
                    lines.append("- 风险项目：")
                    for risk in risks[:5]:
                        lines.append(f"  - {risk['project_name']}：{risk['score']} 分，{'；'.join(risk['reasons'])}")
                else:
                    lines.append("- 当前没有显著风险项目。")
            elif "tickets" in observation:
                tickets = observation["tickets"]
                lines.append(f"- 查询到 {len(tickets)} 条工单。")
                for ticket in tickets[:5]:
                    lines.append(f"  - #{ticket['id']} {ticket['title']}（{ticket['priority']} / {ticket['status']}）")
            elif "projects" in observation:
                projects = observation["projects"]
                lines.append(f"- 查询到 {len(projects)} 个项目。")
                for project in projects[:5]:
                    lines.append(f"  - {project['name']}：{project['stage']}，风险 {project['risk_level']}")
            elif "documents" in observation:
                docs = observation["documents"]
                lines.append(f"- 知识库命中 {len(docs)} 条。")
                for doc in docs:
                    lines.append(f"  - {doc['title']}：{doc['content']}")
            else:
                lines.append(f"- {tool}: {observation}")
        return "\n".join(lines)
