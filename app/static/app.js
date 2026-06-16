const state = {
  user: null,
  view: "agent",
  options: { customers: [], projects: [], users: [] },
  editing: null,
  trace: [],
};

const navItems = [
  { id: "agent", label: "智能助手" },
  { id: "dashboard", label: "经营看板" },
  { id: "customers", label: "客户管理" },
  { id: "projects", label: "项目管理" },
  { id: "contracts", label: "合同审批" },
  { id: "tickets", label: "工单处理" },
  { id: "approvals", label: "审批流" },
  { id: "audit-logs", label: "可观测日志", roles: ["admin", "manager", "finance"] },
  { id: "users", label: "用户权限", roles: ["admin"] },
];

const resourceConfig = {
  customers: {
    title: "客户管理",
    columns: [
      ["name", "客户名称"],
      ["industry", "行业"],
      ["contact_name", "联系人"],
      ["phone", "电话"],
      ["status", "状态"],
      ["owner_name", "负责人"],
    ],
    fields: [
      field("name", "客户名称", "text", true),
      field("industry", "行业"),
      field("contact_name", "联系人"),
      field("phone", "电话"),
      field("email", "邮箱"),
      field("status", "状态", "select", false, [["prospect", "潜在"], ["active", "合作中"], ["inactive", "停用"]]),
      field("owner_id", "负责人", "users"),
    ],
  },
  projects: {
    title: "项目管理",
    columns: [
      ["name", "项目名称"],
      ["customer_name", "客户"],
      ["stage", "阶段"],
      ["budget", "预算"],
      ["risk_level", "风险"],
      ["owner_name", "负责人"],
    ],
    fields: [
      field("customer_id", "客户", "customers", true),
      field("name", "项目名称", "text", true),
      field("stage", "阶段", "select", false, [["initiating", "启动"], ["running", "执行"], ["delivery", "交付"], ["closed", "关闭"]]),
      field("budget", "预算", "number"),
      field("start_date", "开始日期", "date"),
      field("end_date", "结束日期", "date"),
      field("owner_id", "负责人", "users"),
      field("risk_level", "风险等级", "select", false, [["low", "低"], ["middle", "中"], ["high", "高"]]),
    ],
  },
  contracts: {
    title: "合同审批",
    columns: [
      ["contract_no", "合同编号"],
      ["project_name", "项目"],
      ["customer_name", "客户"],
      ["amount", "金额"],
      ["status", "状态"],
      ["payment_status", "回款"],
    ],
    fields: [
      field("project_id", "项目", "projects", true),
      field("contract_no", "合同编号", "text", true),
      field("amount", "金额", "number"),
      field("status", "状态", "select", false, [["pending", "待审批"], ["active", "生效"], ["closed", "关闭"], ["rejected", "驳回"]]),
      field("sign_date", "签约日期", "date"),
      field("due_date", "到期日期", "date"),
      field("payment_status", "回款状态", "select", false, [["unpaid", "未回款"], ["partial", "部分"], ["paid", "已回款"]]),
    ],
  },
  tickets: {
    title: "工单处理",
    columns: [
      ["id", "编号"],
      ["title", "标题"],
      ["project_name", "项目"],
      ["priority", "优先级"],
      ["status", "状态"],
      ["assignee_name", "处理人"],
    ],
    fields: [
      field("project_id", "项目", "projects", true),
      field("title", "标题", "text", true),
      field("priority", "优先级", "select", false, [["low", "低"], ["normal", "普通"], ["high", "高"], ["urgent", "紧急"]]),
      field("status", "状态", "select", false, [["open", "待处理"], ["processing", "处理中"], ["resolved", "已解决"], ["closed", "已关闭"]]),
      field("assignee_id", "处理人", "users"),
      field("description", "描述", "textarea"),
    ],
  },
  users: {
    title: "用户权限",
    columns: [
      ["username", "用户名"],
      ["display_name", "姓名"],
      ["role", "角色"],
      ["department", "部门"],
      ["active", "启用"],
    ],
    fields: [
      field("username", "用户名", "text", true),
      field("password", "密码", "password"),
      field("display_name", "姓名", "text", true),
      field("role", "角色", "select", false, [["admin", "系统管理员"], ["manager", "项目经理"], ["finance", "财务专员"], ["staff", "实施工程师"]]),
      field("department", "部门"),
      field("active", "启用", "select", false, [[1, "启用"], [0, "停用"]]),
    ],
  },
};

function field(name, label, type = "text", required = false, options = []) {
  return { name, label, type, required, options };
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
    ...options,
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error || "请求失败");
  return data;
}

function canSee(item) {
  return !item.roles || item.roles.includes(state.user.role) || state.user.role === "admin";
}

function canMutate(resource) {
  if (state.user.role === "admin") return true;
  if (resource === "customers") return ["manager", "staff"].includes(state.user.role);
  if (resource === "projects") return state.user.role === "manager";
  if (resource === "contracts") return ["manager", "finance"].includes(state.user.role);
  if (resource === "tickets") return ["manager", "staff"].includes(state.user.role);
  return false;
}

function html(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  }[char]));
}

function statusClass(value) {
  const danger = ["high", "urgent", "rejected", "open"];
  const warn = ["middle", "pending", "processing", "partial", "unpaid"];
  if (danger.includes(String(value))) return "status danger";
  if (warn.includes(String(value))) return "status warn";
  return "status";
}

function setTitle(title) {
  document.querySelector("#page-title").textContent = title;
}

async function loadOptions() {
  state.options = await api("/api/options");
}

async function init() {
  try {
    const { user } = await api("/api/me");
    state.user = user;
    await loadOptions();
    showApp();
  } catch {
    document.querySelector("#login-screen").classList.remove("hidden");
  }
}

function showApp() {
  document.querySelector("#login-screen").classList.add("hidden");
  document.querySelector("#app").classList.remove("hidden");
  document.querySelector("#user-name").textContent = `${state.user.display_name} · ${state.user.role_label || state.user.role}`;
  renderNav();
  render();
}

function renderNav() {
  const nav = document.querySelector("#nav");
  nav.innerHTML = navItems.filter(canSee).map((item) => (
    `<button type="button" data-view="${item.id}" class="${state.view === item.id ? "active" : ""}">${item.label}</button>`
  )).join("");
  nav.querySelectorAll("button").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      renderNav();
      render();
    });
  });
}

async function render() {
  if (state.view === "agent") return renderAgent();
  if (state.view === "dashboard") return renderDashboard();
  if (state.view === "approvals") return renderApprovals();
  if (state.view === "audit-logs") return renderAudit();
  return renderResource(state.view);
}

async function renderDashboard() {
  setTitle("经营看板");
  const data = await api("/api/dashboard");
  const metrics = [
    ["客户总数", data.metrics.customers],
    ["活跃项目", data.metrics.active_projects],
    ["合同金额", Number(data.metrics.contract_amount).toLocaleString()],
    ["未关闭工单", data.metrics.open_tickets],
    ["待审批", data.metrics.pending_approvals],
  ];
  document.querySelector("#content").innerHTML = `
    <section class="metrics">${metrics.map(([label, value]) => `<article class="panel metric"><span>${label}</span><strong>${value}</strong></article>`).join("")}</section>
    <section class="grid-2">
      <article class="panel"><header><h3>项目阶段</h3></header>${simpleTable(data.pipeline, [["stage","阶段"],["count","数量"],["budget","预算"]])}</article>
      <article class="panel"><header><h3>近期工单</h3></header>${simpleTable(data.recent_tickets, [["title","标题"],["priority","优先级"],["status","状态"]])}</article>
    </section>
  `;
}

async function renderAgent() {
  setTitle("智能运营助手");
  document.querySelector("#content").innerHTML = `
    <section class="agent-layout">
      <article class="panel chat-box">
        <div id="messages" class="messages">
          <div class="message agent">你好，我可以查询经营指标、分析项目风险、生成周报、自动派单，也可以通过工具审批合同。</div>
        </div>
        <form id="agent-form" class="agent-input">
          <input id="agent-input" autocomplete="off" placeholder="例如：生成本周企业经营周报">
          <button type="submit">发送</button>
        </form>
      </article>
      <aside class="panel">
        <header><h3>演示指令</h3></header>
        <div class="quick-actions">
          <button type="button">生成本周企业经营周报</button>
          <button type="button">分析当前高风险项目并给出预警</button>
          <button type="button">请把 4 号紧急工单自动派单</button>
          <button type="button">通过合同 HT-2026-003</button>
        </div>
        <header><h3>工具调用轨迹</h3></header>
        <div id="trace" class="trace-list">${renderTrace()}</div>
      </aside>
    </section>
  `;
  document.querySelectorAll(".quick-actions button").forEach((button) => {
    button.addEventListener("click", () => askAgent(button.textContent));
  });
  document.querySelector("#agent-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const input = document.querySelector("#agent-input");
    askAgent(input.value.trim());
    input.value = "";
  });
}

async function askAgent(message) {
  if (!message) return;
  const box = document.querySelector("#messages");
  box.insertAdjacentHTML("beforeend", `<div class="message user">${html(message)}</div>`);
  const pending = document.createElement("div");
  pending.className = "message agent";
  pending.textContent = "正在规划工具调用...";
  box.appendChild(pending);
  box.scrollTop = box.scrollHeight;
  try {
    const result = await api("/api/agent/ask", { method: "POST", body: JSON.stringify({ message }) });
    pending.textContent = result.answer;
    state.trace = result.steps;
    document.querySelector("#trace").innerHTML = renderTrace();
  } catch (error) {
    pending.textContent = error.message;
  }
}

function renderTrace() {
  if (!state.trace.length) return `<p class="muted">等待 Agent 执行后显示。</p>`;
  return state.trace.map((step) => `
    <div class="trace-item">
      <strong>${html(step.tool_name)}</strong>
      <span>${html(step.thought)}</span>
    </div>
  `).join("");
}

async function renderResource(resource) {
  const config = resourceConfig[resource];
  setTitle(config.title);
  const data = await api(`/api/${resource}`);
  document.querySelector("#content").innerHTML = `
    <section class="panel">
      <header>
        <h3>${config.title}</h3>
        <div class="toolbar">
          <input id="table-filter" placeholder="搜索表格">
          ${canMutate(resource) ? `<button type="button" id="create-btn">新增</button>` : ""}
        </div>
      </header>
      <div id="table-host">${resourceTable(resource, data.items)}</div>
    </section>
  `;
  const filter = document.querySelector("#table-filter");
  filter.addEventListener("input", () => {
    const keyword = filter.value.toLowerCase();
    const filtered = data.items.filter((item) => JSON.stringify(item).toLowerCase().includes(keyword));
    document.querySelector("#table-host").innerHTML = resourceTable(resource, filtered);
    bindResourceActions(resource, filtered);
  });
  document.querySelector("#create-btn")?.addEventListener("click", () => openForm(resource));
  bindResourceActions(resource, data.items);
}

function resourceTable(resource, items) {
  const config = resourceConfig[resource];
  const headers = config.columns.map(([, label]) => `<th>${label}</th>`).join("");
  const rows = items.map((item) => `
    <tr>
      ${config.columns.map(([key]) => `<td>${formatCell(key, item[key])}</td>`).join("")}
      <td class="actions">
        ${canMutate(resource) ? `<button type="button" data-action="edit" data-id="${item.id}" class="secondary">编辑</button>` : ""}
        ${["admin", "manager"].includes(state.user.role) && resource !== "users" ? `<button type="button" data-action="delete" data-id="${item.id}" class="danger">删除</button>` : ""}
      </td>
    </tr>
  `).join("");
  return `<div class="table-wrap"><table><thead><tr>${headers}<th>操作</th></tr></thead><tbody>${rows || `<tr><td colspan="${config.columns.length + 1}">暂无数据</td></tr>`}</tbody></table></div>`;
}

function formatCell(key, value) {
  if (["status", "risk_level", "priority", "payment_status", "stage"].includes(key)) {
    return `<span class="${statusClass(value)}">${html(value)}</span>`;
  }
  if (key === "amount" || key === "budget") return Number(value || 0).toLocaleString();
  if (key === "active") return value ? "是" : "否";
  return html(value);
}

function bindResourceActions(resource, items) {
  document.querySelectorAll("[data-action='edit']").forEach((button) => {
    button.addEventListener("click", () => {
      const item = items.find((row) => String(row.id) === button.dataset.id);
      openForm(resource, item);
    });
  });
  document.querySelectorAll("[data-action='delete']").forEach((button) => {
    button.addEventListener("click", async () => {
      if (!confirm("确认删除该记录？")) return;
      await api(`/api/${resource}/${button.dataset.id}`, { method: "DELETE" });
      render();
    });
  });
}

function openForm(resource, item = null) {
  state.editing = { resource, item };
  const dialog = document.querySelector("#entity-dialog");
  document.querySelector("#dialog-title").textContent = item ? `编辑${resourceConfig[resource].title}` : `新增${resourceConfig[resource].title}`;
  document.querySelector("#form-error").textContent = "";
  document.querySelector("#form-fields").innerHTML = resourceConfig[resource].fields.map((spec) => renderField(spec, item)).join("");
  dialog.showModal();
}

function renderField(spec, item) {
  const value = item?.[spec.name] ?? "";
  const required = spec.required ? "required" : "";
  if (spec.type === "textarea") {
    return `<label>${spec.label}<textarea name="${spec.name}" ${required}>${html(value)}</textarea></label>`;
  }
  if (["customers", "projects", "users"].includes(spec.type)) {
    const source = state.options[spec.type] || [];
    return `<label>${spec.label}<select name="${spec.name}" ${required}><option value="">请选择</option>${source.map((option) => `<option value="${option.id}" ${String(value) === String(option.id) ? "selected" : ""}>${html(option.name || option.display_name)}</option>`).join("")}</select></label>`;
  }
  if (spec.type === "select") {
    return `<label>${spec.label}<select name="${spec.name}" ${required}>${spec.options.map(([optionValue, label]) => `<option value="${optionValue}" ${String(value) === String(optionValue) ? "selected" : ""}>${label}</option>`).join("")}</select></label>`;
  }
  return `<label>${spec.label}<input name="${spec.name}" type="${spec.type}" value="${html(value)}" ${required}></label>`;
}

async function renderApprovals() {
  setTitle("审批流");
  const data = await api("/api/approvals");
  document.querySelector("#content").innerHTML = `
    <section class="panel">
      <header><h3>审批流</h3></header>
      <div class="table-wrap">
        <table>
          <thead><tr><th>对象</th><th>金额</th><th>申请人</th><th>状态</th><th>意见</th><th>操作</th></tr></thead>
          <tbody>${data.items.map((item) => `
            <tr>
              <td>${html(item.target_name)}</td>
              <td>${Number(item.target_amount || 0).toLocaleString()}</td>
              <td>${html(item.applicant_name)}</td>
              <td><span class="${statusClass(item.status)}">${html(item.status)}</span></td>
              <td>${html(item.comment)}</td>
              <td class="actions">${item.status === "pending" && ["admin","manager","finance"].includes(state.user.role) ? `<button data-approval="${item.id}" data-decision="approved">通过</button><button class="danger" data-approval="${item.id}" data-decision="rejected">驳回</button>` : ""}</td>
            </tr>
          `).join("")}</tbody>
        </table>
      </div>
    </section>`;
  document.querySelectorAll("[data-approval]").forEach((button) => {
    button.addEventListener("click", async () => {
      await api(`/api/approvals/${button.dataset.approval}/decision`, {
        method: "POST",
        body: JSON.stringify({ decision: button.dataset.decision, comment: "Web 审批处理" }),
      });
      renderApprovals();
    });
  });
}

async function renderAudit() {
  setTitle("可观测日志");
  const data = await api("/api/audit-logs");
  document.querySelector("#content").innerHTML = `
    <section class="panel"><header><h3>审计日志</h3></header>${simpleTable(data.items, [["created_at","时间"],["actor_name","用户"],["action","动作"],["entity","对象"],["detail","详情"]])}</section>
  `;
}

function simpleTable(items, columns) {
  return `<div class="table-wrap"><table><thead><tr>${columns.map(([, label]) => `<th>${label}</th>`).join("")}</tr></thead><tbody>${items.map((item) => `<tr>${columns.map(([key]) => `<td>${formatCell(key, item[key])}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

document.querySelector("#login-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  try {
    const { user } = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({ username: form.get("username"), password: form.get("password") }),
    });
    state.user = user;
    await loadOptions();
    showApp();
  } catch (error) {
    document.querySelector("#login-error").textContent = error.message;
  }
});

document.querySelector("#logout-btn").addEventListener("click", async () => {
  await api("/api/logout", { method: "POST" });
  location.reload();
});

document.querySelector("#dialog-close").addEventListener("click", () => document.querySelector("#entity-dialog").close());
document.querySelector("#dialog-cancel").addEventListener("click", () => document.querySelector("#entity-dialog").close());
document.querySelector("#entity-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const { resource, item } = state.editing;
  const form = new FormData(event.currentTarget);
  const payload = {};
  resourceConfig[resource].fields.forEach((spec) => {
    const value = form.get(spec.name);
    if (spec.name === "password" && !value) return;
    payload[spec.name] = value;
  });
  try {
    await api(item ? `/api/${resource}/${item.id}` : `/api/${resource}`, {
      method: item ? "PUT" : "POST",
      body: JSON.stringify(payload),
    });
    document.querySelector("#entity-dialog").close();
    await loadOptions();
    render();
  } catch (error) {
    document.querySelector("#form-error").textContent = error.message;
  }
});

init();
