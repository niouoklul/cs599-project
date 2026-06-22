# API Spec

## 1. 鉴权

| 方法 | 路径 | 说明 |
|---|---|---|
| POST | `/api/login` | 登录，写入 HttpOnly Session Cookie |
| POST | `/api/logout` | 退出登录 |
| GET | `/api/me` | 当前用户信息 |

登录请求：

```json
{"username":"admin","password":"123456"}
```

## 2. 业务资源 API

| 资源 | 路径 | 方法 |
|---|---|---|
| 客户 | `/api/customers` | GET / POST |
| 客户 | `/api/customers/{id}` | PUT / DELETE |
| 项目 | `/api/projects` | GET / POST |
| 项目 | `/api/projects/{id}` | PUT / DELETE |
| 合同 | `/api/contracts` | GET / POST |
| 合同 | `/api/contracts/{id}` | PUT / DELETE |
| 工单 | `/api/tickets` | GET / POST |
| 工单 | `/api/tickets/{id}` | PUT / DELETE |
| 用户 | `/api/users` | GET / POST |
| 用户 | `/api/users/{id}` | PUT |

## 3. Agent API

### POST `/api/agent/ask`

输入自然语言任务，返回答案和工具调用步骤。
若配置 `FREE_DEEPSEEK_API_KEY` 或 `SILICONFLOW_API_KEY`，系统优先使用免费 DeepSeek 兼容 API Tool Calling Planner；否则可继续读取官方 `DEEPSEEK_API_KEY`，最后回退到本地规则 Planner。远程 Planner 失败时会自动回退。

请求：

```json
{"message":"分析当前高风险项目并给出预警"}
```

响应：

```json
{
  "run_id": 1,
  "answer": "我已完成本次 Agent 工具调用...",
  "steps": [
    {
      "type": "tool_result",
      "tool_name": "analyze_project_risks",
      "tool_args": {},
      "observation": {"risks": []}
    }
  ]
}
```

### GET `/api/agent/stream?message=...`

SSE 流式返回 Agent 计划、工具开始、工具结果和最终答案。

事件类型：

| event | 含义 |
|---|---|
| plan | 规划完成 |
| tool_start | 即将调用工具 |
| tool_result | 工具调用完成 |
| final | 最终答复 |

### GET `/api/agent/runs`

返回最近 Agent 运行记录。仅管理员和项目经理可查看。

### GET `/api/agent/runs/{id}`

返回指定 run 的工具步骤。

## 4. MCP / Tool API

### GET `/api/mcp/tools`

返回工具注册表，用于说明 Function Calling 工具。

### POST `/api/mcp/call`

调用指定工具。

```json
{
  "name": "search_projects",
  "arguments": {"risk_level": "high"}
}
```

## 5. 权限矩阵

| 功能 | admin | manager | finance | staff |
|---|---|---|---|---|
| 看板 | Y | Y | Y | Y |
| 客户 | Y | Y | R | Y |
| 项目 | Y | Y | R | R |
| 合同 | Y | Y | Y | R |
| 工单 | Y | Y | R | Y |
| 审批 | Y | Y | Y | R |
| 用户 | Y | N | N | N |
| 审计日志 | Y | Y | Y | N |
| Agent 查询 | Y | Y | Y | Y |
| Agent 写操作 | 按业务角色控制 | 按业务角色控制 | 按业务角色控制 | 按业务角色控制 |
