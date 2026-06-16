# cs599-project

课程：企业级应用软件设计与开发（AI 驱动的软件开发与 Agentic AI）  
课程代码：50120224001 / CS599  
方向：方向二，企业级应用软件的 Agent 改造  
项目名称：企业项目协同系统的智能运营 Agent 改造

## 1. 项目简介

本项目先构建一个模拟企业项目协同系统，覆盖客户、项目、合同、工单、审批、用户权限和审计日志等典型企业后台模块；再用 Agentic AI 技术进行智能化改造，加入“智能运营 Agent”。

改造后的系统支持：

- 自然语言生成企业经营周报
- 自动分析高风险项目并解释风险来源
- 根据负载和规则自动派单
- 通过工具调用完成合同审批
- 从企业知识库检索审批、风险、派单和周报规则
- 保存 Agent run、step、tool observation 和业务审计日志
- 通过 benchmark 评估 Agent 行为是否调用了正确工具

## 2. 课程要求对应关系

| 要求 | 本项目实现 |
|---|---|
| SDD 规格驱动开发 | `docs/specs/product_spec.md`、`architecture_spec.md`、`api_spec.md` |
| 工具使用 / Function Calling | `app/agent/tools.py` 工具注册表与 `call_tool` |
| 记忆机制 | `agent_memories` 表保存跨轮对话 |
| 状态管理与多步骤推理 | `EnterpriseAgent.run_stream` 执行 plan -> tool -> observation -> final |
| Agentic RAG | `knowledge_base` + `search_knowledge` |
| MCP 协议 | `scripts/mcp_server.py` 提供 stdio JSON-RPC 工具服务 |
| 可观测性与评估 | `agent_runs`、`agent_steps`、`audit_logs`、`scripts/benchmark_agent.py` |
| GitHub 交付 | `LICENSE`、`README`、`Dockerfile`、`.github/workflows/ci.yml` |

## 3. 目录结构

```text
cs599-project/
  app/
    agent/              # Agent 规划器、LLM 可选 Planner、工具、记忆、追踪
    static/             # Web 前端
    database.py         # SQLite 初始化与连接
    schema.sql          # 业务表、知识库、Agent 记忆表、追踪表
    seed.py             # 演示数据
    server.py           # Web API 与静态资源服务
  docs/
    specs/              # SDD 规格文档
    demo_guide.md       # 答辩演示脚本
    submission_checklist.md
    CS599_大作业报告.md
    CS599_大作业报告.pdf
  eval/
    benchmark_cases.json
  scripts/
    benchmark_agent.py
    demo_api.py
    generate_report_pdf.py
    mcp_server.py
    reset_demo_data.py
  tests.py
  run.py
```

## 4. 快速运行

建议 Python 3.10+。

```bash
python run.py
```

浏览器打开：

```text
http://127.0.0.1:8000
```

演示账号：

| 用户名 | 密码 | 角色 |
|---|---|---|
| admin | 123456 | 系统管理员 |
| manager | 123456 | 项目经理 |
| finance | 123456 | 财务专员 |
| staff | 123456 | 实施工程师 |

## 5. 免费 DeepSeek API 接入

系统优先支持免费 DeepSeek 兼容 API Tool Calling。推荐使用 SiliconFlow 等 OpenAI 兼容平台提供的 DeepSeek 免费额度/免费模型：配置 `FREE_DEEPSEEK_API_KEY` 后，Agent 会把业务工具注册为 `tools`，由远程 DeepSeek 模型返回 `tool_calls`，再由本地系统执行这些工具。没有 API Key、免费额度耗尽或接口失败时，系统自动回退到本地 deterministic planner，答辩时仍可完整演示。

```bash
set FREE_DEEPSEEK_API_KEY=your_free_api_key
set FREE_DEEPSEEK_BASE_URL=https://api.siliconflow.cn/v1
set FREE_DEEPSEEK_MODEL=deepseek-ai/DeepSeek-V3.2
python run.py
```

如果需要使用官方 DeepSeek API，也可配置 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。官方 DeepSeek API 按 token 扣费，本项目默认推荐免费兼容 API。

禁用远程 LLM：

```bash
set AGENT_DISABLE_LLM=1
```

真实 API Key 不得提交到仓库。

## 6. 测试与评估

```bash
python tests.py
python scripts/benchmark_agent.py
python scripts/smoke_web.py
python scripts/validate_report_docx.py
```

Benchmark 输出包含工具调用命中率、回答关键词命中率和通过状态。当前用例覆盖风险分析、经营周报和工单派单。
`smoke_web.py` 会临时启动 Web 服务并自动关闭，适合在提交前确认首页、登录、看板和 Agent API 都可用。

运行已启动服务的 API 演示：

```bash
python scripts/demo_api.py
```

## 7. Docker 部署

```bash
docker compose up --build
```

打开：

```text
http://127.0.0.1:8000
```

## 8. WSL 运行

Windows 下也可以在 WSL 中运行：

```bash
cd /mnt/c/Users/19111/Desktop/work/cs599-project
python3 run.py
```

## 9. MCP 工具服务

启动 stdio JSON-RPC 工具服务：

```bash
python scripts/mcp_server.py
```

示例请求：

```json
{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}
```

## 10. 推荐答辩演示路径

1. 登录 `admin / 123456`。
2. 打开“经营看板”，说明这是改造前传统企业后台。
3. 打开“智能助手”，输入“生成本周企业经营周报”。
4. 输入“分析当前高风险项目并给出预警”，展示 Agentic RAG + 风险工具。
5. 输入“请把 4 号紧急工单自动派单”，展示 Function Calling 写入业务数据。
6. 输入“通过合同 HT-2026-003”，展示审批工具调用。
7. 打开“可观测日志”，展示审计记录。
8. 运行 `python scripts/benchmark_agent.py`，展示 Agent 行为评估。

## 11. GitHub 提交说明

- 仓库名应为 `cs599-project`。
- Public 仓库已包含 `LICENSE`。
- 如改为 Private Repository，请在 GitHub 添加 `qxr777` 为 Collaborator。
- 不要提交真实 API Key。
- 最终报告路径：`docs/CS599_大作业报告.pdf`。
- Word 优化版路径：`docs/CS599_大作业报告_程辉高.docx`。

## 12. 引用与学术纪律

本仓库代码由课程项目需求驱动实现，未复制外部开源项目代码。使用的协议、方法论和参考概念包括 Function Calling、MCP、Agentic RAG、SDD、ReAct/状态机式多步骤推理等，均在报告和规格文档中说明。
