# Demo Guide

## 演示目标

用 5 分钟展示“传统企业后台”如何被 Agent 改造为“自然语言目标驱动的智能运营系统”。

## 演示前准备

```bash
python scripts/reset_demo_data.py
python run.py
```

打开 `http://127.0.0.1:8000`，使用 `admin / 123456` 登录。

## 5 分钟演示脚本

### 0:00 - 0:40 背景

说明原始系统是企业项目协同后台，包含客户、项目、合同、工单和审批。痛点是数据分散、跨页面查询成本高、风险分析和派单依赖人工。

### 0:40 - 1:30 改造前

打开“经营看板”“项目管理”“工单处理”，展示数据存在但需要人工综合判断。

### 1:30 - 2:30 经营周报 Agent

进入“智能助手”，输入：

```text
生成本周企业经营周报
```

讲解 Agent 调用了 `get_dashboard_metrics`、`analyze_project_risks`、`generate_weekly_report`。

### 2:30 - 3:20 风险分析 Agent

输入：

```text
分析当前高风险项目并给出预警
```

讲解 Agent 使用知识库规则和风险分析工具，合并项目、合同、工单信息。

### 3:20 - 4:10 工单派单与合同审批

输入：

```text
请把 4 号紧急工单自动派单
```

再输入：

```text
通过合同 HT-2026-003
```

说明 Agent 不只是回答文本，而是通过工具修改业务数据并写入审计日志。

### 4:10 - 5:00 可观测性与评估

打开“可观测日志”，说明系统记录业务审计。运行：

```bash
python scripts/benchmark_agent.py
```

展示工具调用命中率和关键词命中率。

## 备用方案

如果远程 LLM API 不可用，设置：

```bash
set AGENT_DISABLE_LLM=1
```

系统会使用本地规则规划器，仍可完整演示。

## 提交前 Smoke Test

无需手动启动服务即可验证 Web 闭环：

```bash
python scripts/smoke_web.py
```

WSL 下可运行：

```bash
cd /mnt/c/Users/19111/Desktop/work/cs599-project
python3 scripts/smoke_web.py
```
