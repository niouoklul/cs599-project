# Architecture Spec

## 1. 总体架构

```mermaid
flowchart LR
    U[用户/评审] --> UI[Web 前端]
    UI --> API[Python HTTP API]
    API --> Auth[Session + RBAC]
    API --> Biz[企业业务模块]
    API --> Agent[智能运营 Agent]
    Biz --> DB[(SQLite)]
    Agent --> Planner[免费 DeepSeek API Planner / 本地规则回退]
    Agent --> Tools[Function Calling 工具层]
    Agent --> Memory[长期记忆]
    Agent --> Trace[运行轨迹]
    Tools --> DB
    Tools --> KB[企业知识库 RAG]
    Memory --> DB
    Trace --> DB
```

## 2. Agent 交互流程

```mermaid
sequenceDiagram
    participant User as 用户
    participant UI as 前端
    participant API as /api/agent/ask
    participant Agent as EnterpriseAgent
    participant Tools as Tool Registry
    participant DB as SQLite

    User->>UI: 输入自然语言任务
    UI->>API: POST message
    API->>Agent: 创建 run，读取历史记忆
    Agent->>Agent: Planner 生成工具调用计划
    loop 每个工具步骤
        Agent->>Tools: call_tool(name,args)
        Tools->>DB: 查询或更新业务数据
        Tools-->>Agent: observation
        Agent->>DB: 写入 agent_steps
    end
    Agent->>DB: 写入 assistant 记忆与 run 结果
    Agent-->>API: answer + steps
    API-->>UI: 展示答案和工具轨迹
```

## 3. 数据流设计

```mermaid
flowchart TD
    A[自然语言输入] --> B[Planner]
    B --> C{任务类型}
    C -->|周报| D[get_dashboard_metrics]
    C -->|风险| E[analyze_project_risks]
    C -->|派单| F[route_ticket]
    C -->|审批| G[approve_contract]
    C -->|规则解释| H[search_knowledge]
    D --> I[Observation]
    E --> I
    F --> I
    G --> I
    H --> I
    I --> J[Answer Composer]
    J --> K[用户可读答复]
    I --> L[agent_steps]
    K --> M[agent_memories]
```

## 4. 分层结构

| 层级 | 文件 | 职责 |
|---|---|---|
| 表现层 | `app/static/*` | 登录、看板、业务表格、智能助手 |
| 控制层 | `app/server.py` | API 路由、鉴权、静态资源 |
| Agent 层 | `app/agent/agent.py` | 规划、执行、答案组织 |
| 工具层 | `app/agent/tools.py` | Function Calling 工具定义与实现 |
| 记忆与追踪 | `app/agent/memory.py` | run、step、memory 持久化 |
| 数据层 | `app/schema.sql`、`app/database.py` | SQLite 表结构与连接 |

## 5. 改造前 vs 改造后

| 维度 | 改造前 | 改造后 |
|---|---|---|
| 交互方式 | 菜单、表格、人工筛选 | 自然语言任务驱动 |
| 风险分析 | 人工跨模块汇总 | Agent 自动合并项目、合同、工单 |
| 工单派单 | 人工查看人员负载 | Tool Use 自动选择处理人 |
| 合同审批 | 人工进入审批页面 | Agent 调用审批工具并写审计 |
| 报告生成 | 手工统计 | 自动生成经营周报 |
| 可解释性 | 操作日志有限 | run/step/tool observation 全链路留痕 |

## 6. 扩展路线

- Planner 替换为 LangGraph 状态图，实现条件分支和失败重试。
- 接入免费 DeepSeek 兼容 API，实现真实 LLM Function Calling；当前已提供免费 API 优先、官方 API 备用和本地规则回退。
- 将知识库替换为向量数据库，实现语义 RAG。
- 将 SQLite 替换为 PostgreSQL/MySQL，并接入企业统一认证。
- 接入 OpenTelemetry 或 LangSmith 类 tracing 平台。
