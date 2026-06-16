from pathlib import Path
import os

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS_DIR = Path(os.environ.get("REPORT_DOCS_DIR", ROOT / "docs"))
OUT = DOCS_DIR / "CS599_大作业报告.pdf"
STUDENT_ID = os.environ.get("STUDENT_ID", "2025302979")
STUDENT_NAME = os.environ.get("STUDENT_NAME", "程辉高")
STUDENT_MAJOR = os.environ.get("STUDENT_MAJOR", "计算机技术 / 软件工程")


class OutlineDocTemplate(SimpleDocTemplate):
    def afterFlowable(self, flowable):
        if hasattr(flowable, "_outline"):
            title, key, level = flowable._outline
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(title, key, level=level, closed=False)


def heading(text, styles, level=0):
    style = styles["Heading1"] if level == 0 else styles["Heading2"]
    paragraph = Paragraph(text, style)
    key = f"bookmark_{abs(hash((text, level))) % 100000000}"
    paragraph._outline = (text, key, level)
    return paragraph


def para(text, styles):
    return Paragraph(text, styles["Body"])


def bullet(text, styles):
    return Paragraph(f"• {text}", styles["Body"])


def make_table(data, widths=None):
    table = Table(data, colWidths=widths, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#17202A")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#D8DEE9")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def build_styles():
    pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))
    base = getSampleStyleSheet()
    return {
        "Title": ParagraphStyle(
            "TitleCN",
            parent=base["Title"],
            fontName="STSong-Light",
            fontSize=24,
            leading=32,
            alignment=TA_CENTER,
            spaceAfter=18,
        ),
        "Subtitle": ParagraphStyle(
            "SubtitleCN",
            parent=base["Normal"],
            fontName="STSong-Light",
            fontSize=13,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#475467"),
        ),
        "Heading1": ParagraphStyle(
            "Heading1CN",
            parent=base["Heading1"],
            fontName="STSong-Light",
            fontSize=16,
            leading=22,
            textColor=colors.HexColor("#1F4D78"),
            spaceBefore=14,
            spaceAfter=8,
        ),
        "Heading2": ParagraphStyle(
            "Heading2CN",
            parent=base["Heading2"],
            fontName="STSong-Light",
            fontSize=13,
            leading=18,
            textColor=colors.HexColor("#2563A9"),
            spaceBefore=10,
            spaceAfter=6,
        ),
        "Body": ParagraphStyle(
            "BodyCN",
            parent=base["BodyText"],
            fontName="STSong-Light",
            fontSize=10.5,
            leading=16,
            alignment=TA_LEFT,
            spaceAfter=6,
        ),
        "Small": ParagraphStyle(
            "SmallCN",
            parent=base["BodyText"],
            fontName="STSong-Light",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#667085"),
        ),
    }


def story():
    styles = build_styles()
    s = []

    s.append(Spacer(1, 0.45 * inch))
    s.append(Paragraph("《企业级应用软件设计与开发》期末大作业报告", styles["Title"]))
    s.append(Paragraph("企业项目协同系统的智能运营 Agent 改造", styles["Subtitle"]))
    s.append(Spacer(1, 0.5 * inch))
    cover = [
        ["字段", "内容"],
        ["课程名称", "企业级应用软件设计与开发"],
        ["项目名称", "企业项目协同系统的智能运营 Agent 改造"],
        ["方向", "方向二：企业级应用软件的 Agent 改造"],
        ["学号", STUDENT_ID],
        ["姓名", STUDENT_NAME],
        ["专业", STUDENT_MAJOR],
        ["指导教师", "戚欣"],
        ["提交日期", "2026 年 6 月 22 日"],
    ]
    s.append(make_table(cover, [1.55 * inch, 4.7 * inch]))
    s.append(Spacer(1, 0.25 * inch))
    s.append(Paragraph("说明：提交前请将学号、姓名、专业替换为本人真实信息，并补充 AI IDE 使用截图。", styles["Small"]))
    s.append(PageBreak())

    s.append(heading("目录", styles, 0))
    for item in [
        "一、选题背景与设计思想",
        "二、Specs 规格文档",
        "三、系统架构与设计",
        "四、关键实现与代码展示",
        "五、测试与评估",
        "六、系统升级与扩展",
        "七、课程总结",
    ]:
        s.append(bullet(item, styles))
    s.append(PageBreak())

    s.append(heading("一、选题背景与设计思想", styles, 0))
    s.append(para("本项目选择方向二：企业级应用软件的 Agent 改造。项目先构建一个模拟企业项目协同系统，覆盖客户、项目、合同、工单、审批和审计日志等企业后台模块，然后叠加智能运营 Agent，使系统从被动表单操作升级为自然语言任务驱动。", styles))
    s.append(para("原始系统的主要痛点包括数据分散、流程依赖人工、周报生成成本高、规则难复用和智能行为不可解释。本项目的改造目标是把业务数据、流程规则和权限边界封装为工具，由 Agent 根据任务目标选择工具并执行多步骤操作。", styles))
    s.append(
        make_table(
            [
                ["痛点", "改造前", "改造后"],
                ["数据分散", "跨客户、项目、合同、工单人工查找", "Agent 汇聚多表数据输出风险原因"],
                ["流程低效", "派单和审批依赖人工判断", "工具调用自动派单和审批"],
                ["报告成本", "手工复制指标", "一键生成经营周报"],
                ["可解释性", "只有基础审计日志", "保存 run、step、tool observation"],
            ],
            [1.2 * inch, 2.35 * inch, 2.7 * inch],
        )
    )

    s.append(heading("二、Specs 规格文档", styles, 0))
    s.append(para("本项目采用 SDD 规格驱动开发，规格文档位于 docs/specs。Product Spec 定义用户角色、业务痛点和验收标准；Architecture Spec 定义总体架构、Agent 流程和数据流；API Spec 固化鉴权、业务资源、Agent 和 MCP/Tool API。", styles))
    s.append(
        make_table(
            [
                ["规格", "核心内容"],
                ["Product Spec", "项目定位、原始系统痛点、用户故事、非功能要求、验收标准"],
                ["Architecture Spec", "分层架构、Agent 交互流程、数据流、改造前后对比"],
                ["API Spec", "登录、业务资源、Agent、SSE、MCP 工具和权限矩阵"],
            ],
            [1.55 * inch, 4.7 * inch],
        )
    )

    s.append(heading("三、系统架构与设计", styles, 0))
    s.append(para("系统由 Web 前端、Python HTTP API、Session + RBAC、企业业务模块、EnterpriseAgent、工具层、记忆层、运行轨迹和 SQLite 数据库组成。Agent 不是独立聊天页面，而是直接连接业务数据和业务写操作。", styles))
    s.append(
        make_table(
            [
                ["层级", "文件", "职责"],
                ["表现层", "app/static/*", "登录、看板、业务表格、智能助手"],
                ["控制层", "app/server.py", "API 路由、鉴权、静态资源"],
                ["Agent 层", "app/agent/agent.py", "规划、执行、答案组织"],
                ["工具层", "app/agent/tools.py", "Function Calling 工具定义与实现"],
                ["记忆与追踪", "app/agent/memory.py", "run、step、memory 持久化"],
                ["数据层", "app/schema.sql", "业务表、知识库、Agent 轨迹表"],
            ],
            [1.15 * inch, 1.65 * inch, 3.45 * inch],
        )
    )
    s.append(heading("Agent 交互流程", styles, 1))
    for step in [
        "用户输入自然语言任务。",
        "Agent 创建 run，读取最近对话记忆。",
        "Planner 生成工具调用计划。",
        "工具层读取或更新业务数据库。",
        "每一步 observation 写入 agent_steps。",
        "Answer Composer 生成最终答复并写入长期记忆。",
    ]:
        s.append(bullet(step, styles))

    s.append(heading("四、关键实现与代码展示", styles, 0))
    s.append(para("Agent 核心循环位于 app/agent/agent.py。默认 planner 为 deterministic planner，保证无外部 API Key 时也能在答辩现场稳定演示。工具定义位于 app/agent/tools.py，覆盖经营指标、项目查询、工单查询、工单派单、风险分析、周报生成、合同审批和知识库检索。", styles))
    s.append(para("系统还提供免费 DeepSeek 兼容 API Planner，位于 app/agent/llm.py。配置 FREE_DEEPSEEK_API_KEY 或 SILICONFLOW_API_KEY 后，系统会将企业工具注册为 tools，由远程 DeepSeek 兼容接口返回 tool_calls；官方 DEEPSEEK_API_KEY 仅作为备用，远程 API 不可用时系统自动回退到本地规划器，保证 Demo 稳定性。", styles))
    s.append(
        make_table(
            [
                ["技术点", "实现位置", "说明"],
                ["Function Calling", "app/agent/tools.py", "工具注册表 + call_tool 统一入口"],
                ["记忆机制", "agent_memories", "保存跨轮 user/assistant 记忆"],
                ["状态管理", "agent_runs / agent_steps", "每次运行和每个工具步骤可追踪"],
                ["Agentic RAG", "knowledge_base + search_knowledge", "检索审批、风险、派单和周报规则"],
                ["MCP 融合", "scripts/mcp_server.py", "stdio JSON-RPC 工具服务"],
                ["工程交付", "Dockerfile / CI / demo_api.py", "支持容器部署、自动测试和命令行演示"],
            ],
            [1.4 * inch, 1.8 * inch, 3.05 * inch],
        )
    )
    s.append(para("AI IDE 使用截图需在最终提交前补充。建议截图包括 Specs 编写、Agent 工具实现、测试运行和 Git 提交记录。", styles))

    s.append(heading("五、测试与评估", styles, 0))
    s.append(para("项目提供 tests.py、scripts/benchmark_agent.py、scripts/smoke_web.py 和 scripts/demo_api.py。前者验证密码哈希、Agent 风险分析、登录 API、看板 API 和周报 Agent API；benchmark 评估工具调用命中率和回答关键词命中率；smoke_web 会临时启动 Web 服务验证首页、登录、看板和 Agent API；demo_api 可对已启动服务执行命令行演示。", styles))
    s.append(
        make_table(
            [
                ["用例", "Prompt", "期望工具"],
                ["risk-analysis", "分析当前高风险项目并给出预警", "search_knowledge, analyze_project_risks"],
                ["weekly-report", "生成本周企业经营周报", "get_dashboard_metrics, analyze_project_risks, generate_weekly_report"],
                ["ticket-routing", "请把 4 号紧急工单自动派单", "route_ticket"],
            ],
            [1.25 * inch, 2.45 * inch, 2.55 * inch],
        )
    )
    s.append(para("评估重点不是只看自然语言是否流畅，而是检查 Agent 是否选择正确工具、是否产生可验证的业务动作，以及最终答复是否包含关键业务信息。", styles))

    s.append(heading("六、系统升级与扩展", styles, 0))
    for item in [
        "将 deterministic planner 替换为 LangGraph 状态图，加入条件分支、失败重试和人工确认节点。",
        "继续强化免费 DeepSeek 兼容 API、本地模型和 LangGraph 接入，用真实 LLM Function Calling 生成工具计划。",
        "将 knowledge_base 替换为向量数据库，实现语义检索和文档级 Agentic RAG。",
        "将 SQLite 替换为 PostgreSQL/MySQL，并接入企业统一身份认证。",
        "引入 OpenTelemetry、LangSmith 或自建 LLMOps 平台，实现完整 tracing 和质量评估。",
        "使用 Docker Compose 或云服务器提供可访问 URL，争取部署加分项。",
    ]:
        s.append(bullet(item, styles))

    s.append(heading("七、课程总结", styles, 0))
    s.append(para("本项目最大的收获是：企业级应用的 Agent 改造不是简单加一个聊天框，而是要把业务系统中的数据、流程和权限封装为可控工具，再让 Agent 在规格约束下编排工具完成业务目标。开发者角色也从单纯代码编写者转向规格制定者、工具设计者、状态管理者和行为评估者。", styles))
    s.append(para("课程建议方面，希望后续能增加更多企业真实场景的 Agent 改造案例，并提供统一的 MCP、LangGraph 和 LLMOps 实验模板，帮助学生在有限时间内更深入比较不同 Agent 架构的优缺点。", styles))

    return s


def main():
    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc = OutlineDocTemplate(
        str(OUT),
        pagesize=letter,
        rightMargin=0.85 * inch,
        leftMargin=0.85 * inch,
        topMargin=0.8 * inch,
        bottomMargin=0.8 * inch,
        title="CS599 大作业报告",
        author="CS599 Final Project",
    )
    doc.build(story())
    print(OUT)


if __name__ == "__main__":
    main()
