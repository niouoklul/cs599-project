from .security import hash_password


def seed_database(connection):
    users = [
        ("admin", "系统管理员", "admin", "信息中心"),
        ("manager", "项目经理", "manager", "交付中心"),
        ("finance", "财务专员", "finance", "财务部"),
        ("staff", "实施工程师", "staff", "实施一组"),
    ]
    for username, display_name, role, department in users:
        connection.execute(
            """
            INSERT INTO users (username, password_hash, display_name, role, department)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username, hash_password("123456"), display_name, role, department),
        )

    user_ids = {
        row["username"]: row["id"]
        for row in connection.execute("SELECT id, username FROM users").fetchall()
    }

    customers = [
        ("远航装备集团", "高端制造", "周明", "13800010001", "zhouming@example.com", "active", user_ids["manager"]),
        ("华东云服科技", "软件服务", "林悦", "13800010002", "linyue@example.com", "active", user_ids["manager"]),
        ("北辰医药连锁", "医药零售", "吴倩", "13800010003", "wuqian@example.com", "prospect", user_ids["staff"]),
        ("星原教育集团", "教育培训", "陈立", "13800010004", "chenli@example.com", "active", user_ids["staff"]),
    ]
    for customer in customers:
        connection.execute(
            """
            INSERT INTO customers
                (name, industry, contact_name, phone, email, status, owner_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            customer,
        )

    projects = [
        (1, "MES 生产协同平台", "running", 860000, "2026-03-01", "2026-09-30", user_ids["manager"], "middle"),
        (2, "多租户客户服务系统", "delivery", 520000, "2026-01-15", "2026-07-15", user_ids["manager"], "low"),
        (3, "门店库存数据中台", "initiating", 320000, "2026-06-01", "2026-11-30", user_ids["staff"], "high"),
        (4, "智慧校园工单平台", "running", 410000, "2026-04-10", "2026-10-20", user_ids["staff"], "middle"),
    ]
    for project in projects:
        connection.execute(
            """
            INSERT INTO projects
                (customer_id, name, stage, budget, start_date, end_date, owner_id, risk_level)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            project,
        )

    contracts = [
        (1, "HT-2026-001", 860000, "active", "2026-03-05", "2026-09-30", "partial"),
        (2, "HT-2026-002", 520000, "active", "2026-01-20", "2026-07-15", "paid"),
        (3, "HT-2026-003", 320000, "pending", "2026-06-03", "2026-11-30", "unpaid"),
        (4, "HT-2026-004", 410000, "pending", "2026-04-15", "2026-10-20", "partial"),
    ]
    for contract in contracts:
        connection.execute(
            """
            INSERT INTO contracts
                (project_id, contract_no, amount, status, sign_date, due_date, payment_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            contract,
        )

    tickets = [
        (1, "生产排程导入模板确认", "high", "processing", user_ids["staff"], "客户希望支持 Excel 批量导入并校验异常行。"),
        (1, "设备状态接口联调", "normal", "open", user_ids["staff"], "等待甲方提供测试网关账号。"),
        (2, "验收报告盖章扫描件归档", "normal", "resolved", user_ids["manager"], "已完成线上归档，等待财务确认回款。"),
        (4, "移动端消息推送偶发延迟", "urgent", "open", user_ids["staff"], "需要排查推送服务和校园网出口延迟。"),
    ]
    for ticket in tickets:
        connection.execute(
            """
            INSERT INTO tickets
                (project_id, title, priority, status, assignee_id, description)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            ticket,
        )

    approvals = [
        ("contract", 3, user_ids["staff"], None, "pending", "新签合同待项目经理复核。"),
        ("contract", 4, user_ids["manager"], None, "pending", "回款节点调整后重新提交审批。"),
    ]
    for approval in approvals:
        connection.execute(
            """
            INSERT INTO approvals
                (target_type, target_id, applicant_id, reviewer_id, status, comment)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            approval,
        )

    connection.execute(
        """
        INSERT INTO audit_logs (actor_id, action, entity, entity_id, detail)
        VALUES (?, 'seed', 'system', NULL, '初始化演示数据')
        """,
        (user_ids["admin"],),
    )

    knowledge_items = [
        (
            "合同审批规则",
            "workflow",
            "金额超过 30 万元的合同必须经过项目经理或财务专员审批；审批通过后合同状态变为 active，驳回后状态变为 rejected。",
        ),
        (
            "项目风险分级",
            "risk",
            "高风险项目通常同时具备延期、未关闭紧急工单、待审批合同或客户验收阻塞。Agent 应优先给出风险来源和下一步动作。",
        ),
        (
            "工单自动派单策略",
            "ticket",
            "紧急工单优先分派给当前未关闭工单最少的实施工程师；普通工单可分派给项目负责人或实施组成员。",
        ),
        (
            "周报模板",
            "report",
            "经营周报需要包含客户数量、活跃项目、合同金额、待审批事项、未关闭工单、高风险项目以及建议动作。",
        ),
    ]
    for item in knowledge_items:
        connection.execute(
            "INSERT INTO knowledge_base (title, category, content) VALUES (?, ?, ?)",
            item,
        )
