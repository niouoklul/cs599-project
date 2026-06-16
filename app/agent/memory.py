from .utils import compact_json


def create_run(connection, user_id, message):
    cursor = connection.execute(
        "INSERT INTO agent_runs (user_id, message, status) VALUES (?, ?, 'running')",
        (user_id, message),
    )
    return cursor.lastrowid


def finish_run(connection, run_id, answer, status="completed"):
    connection.execute(
        """
        UPDATE agent_runs
        SET status = ?, answer = ?, finished_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, answer, run_id),
    )


def remember(connection, user_id, role, content):
    connection.execute(
        "INSERT INTO agent_memories (user_id, role, content) VALUES (?, ?, ?)",
        (user_id, role, content[:4000]),
    )


def load_recent_memory(connection, user_id, limit=8):
    rows = connection.execute(
        """
        SELECT role, content, created_at
        FROM agent_memories
        WHERE user_id = ?
        ORDER BY id DESC
        LIMIT ?
        """,
        (user_id, limit),
    ).fetchall()
    return [dict(row) for row in reversed(rows)]


def record_step(connection, run_id, step_index, thought, tool_name, tool_args, observation):
    connection.execute(
        """
        INSERT INTO agent_steps
            (run_id, step_index, thought, tool_name, tool_args, observation)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            run_id,
            step_index,
            thought,
            tool_name,
            compact_json(tool_args),
            compact_json(observation),
        ),
    )


def list_runs(connection, limit=30):
    rows = connection.execute(
        """
        SELECT r.id, r.message, r.status, r.answer, r.started_at, r.finished_at,
               u.display_name AS user_name
        FROM agent_runs r
        LEFT JOIN users u ON u.id = r.user_id
        ORDER BY r.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [dict(row) for row in rows]


def list_steps(connection, run_id):
    rows = connection.execute(
        """
        SELECT step_index, thought, tool_name, tool_args, observation, created_at
        FROM agent_steps
        WHERE run_id = ?
        ORDER BY step_index
        """,
        (run_id,),
    ).fetchall()
    return [dict(row) for row in rows]
