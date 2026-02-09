"""SQLite 异步存储 - 会话、消息和截图持久化

使用 aiosqlite 提供异步 SQLite 存储，数据保存在 data/mobile_agent.db。
"""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS conversations (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL DEFAULT '新对话',
    status TEXT NOT NULL DEFAULT 'success',
    steps INTEGER DEFAULT 0,
    duration TEXT DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    tool_name TEXT DEFAULT '',
    has_image INTEGER DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_messages_conv ON messages(conversation_id, created_at);

CREATE TABLE IF NOT EXISTS screenshots (
    id TEXT PRIMARY KEY,
    data TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


class Storage:
    """SQLite 异步存储"""

    def __init__(self) -> None:
        self._db: aiosqlite.Connection | None = None
        self._db_path: str = ""

    @property
    def is_initialized(self) -> bool:
        return self._db is not None

    async def init(self, db_path: str | None = None) -> None:
        """初始化数据库连接并建表

        Args:
            db_path: 数据库文件路径，默认为 data/mobile_agent.db
        """
        if db_path is None:
            base = Path(__file__).resolve().parent.parent.parent.parent
            data_dir = base / "data"
            data_dir.mkdir(parents=True, exist_ok=True)
            db_path = str(data_dir / "mobile_agent.db")

        self._db_path = db_path
        self._db = await aiosqlite.connect(db_path)
        self._db.row_factory = aiosqlite.Row

        # 开启 WAL 模式 + 外键
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.execute("PRAGMA foreign_keys=ON")
        await self._db.executescript(_SCHEMA)
        await self._db.commit()

        logger.info("Storage 初始化完成: %s", db_path)

    async def close(self) -> None:
        """关闭数据库连接"""
        if self._db:
            await self._db.close()
            self._db = None

    # ── Conversations ─────────────────────────────────────────

    async def save_conversation(
        self,
        conversation_id: str,
        title: str,
        *,
        status: str = "success",
        steps: int = 0,
        duration: str = "",
    ) -> None:
        """保存或更新会话"""
        assert self._db
        await self._db.execute(
            """INSERT INTO conversations (id, title, status, steps, duration)
               VALUES (?, ?, ?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET
                 title=excluded.title,
                 status=excluded.status,
                 steps=excluded.steps,
                 duration=excluded.duration
            """,
            (conversation_id, title, status, steps, duration),
        )
        await self._db.commit()

    async def list_conversations(self, query: str = "") -> list[dict[str, Any]]:
        """列出会话"""
        assert self._db
        if query:
            cursor = await self._db.execute(
                "SELECT * FROM conversations WHERE title LIKE ? ORDER BY created_at DESC",
                (f"%{query}%",),
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM conversations ORDER BY created_at DESC"
            )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_conversation(self, conversation_id: str) -> dict[str, Any] | None:
        """获取会话详情（含消息）"""
        assert self._db
        cursor = await self._db.execute(
            "SELECT * FROM conversations WHERE id=?", (conversation_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None

        conv = dict(row)
        conv["messages"] = await self.get_messages(conversation_id)
        return conv

    async def delete_conversation(self, conversation_id: str) -> bool:
        """删除会话（级联删除消息）"""
        assert self._db
        cursor = await self._db.execute(
            "DELETE FROM conversations WHERE id=?", (conversation_id,)
        )
        await self._db.commit()
        return cursor.rowcount > 0

    # ── Messages ──────────────────────────────────────────────

    async def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        *,
        message_id: str | None = None,
        tool_name: str = "",
        has_image: bool = False,
    ) -> str:
        """添加消息到会话

        如果 conversation 不存在则自动创建。
        """
        assert self._db
        msg_id = message_id or str(uuid.uuid4())

        # 确保会话存在
        cursor = await self._db.execute(
            "SELECT 1 FROM conversations WHERE id=?", (conversation_id,)
        )
        if await cursor.fetchone() is None:
            title = content[:50] + ("..." if len(content) > 50 else "")
            await self.save_conversation(conversation_id, title, status="running")

        await self._db.execute(
            """INSERT INTO messages (id, conversation_id, role, content, tool_name, has_image)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (msg_id, conversation_id, role, content, tool_name, 1 if has_image else 0),
        )
        await self._db.commit()
        return msg_id

    async def get_messages(self, conversation_id: str) -> list[dict[str, Any]]:
        """获取会话的所有消息"""
        assert self._db
        cursor = await self._db.execute(
            "SELECT * FROM messages WHERE conversation_id=? ORDER BY created_at",
            (conversation_id,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Screenshots ───────────────────────────────────────────

    async def save_screenshot(self, data: str) -> str:
        """保存截图，返回 screenshot_id"""
        assert self._db
        screenshot_id = str(uuid.uuid4())
        await self._db.execute(
            "INSERT INTO screenshots (id, data) VALUES (?, ?)",
            (screenshot_id, data),
        )
        # 清理旧截图，保留最近 50 张
        await self._db.execute(
            """DELETE FROM screenshots WHERE id NOT IN (
                 SELECT id FROM screenshots ORDER BY created_at DESC LIMIT 50
               )"""
        )
        await self._db.commit()
        return screenshot_id

    async def get_screenshot(self, screenshot_id: str) -> str | None:
        """获取截图数据"""
        assert self._db
        cursor = await self._db.execute(
            "SELECT data FROM screenshots WHERE id=?", (screenshot_id,)
        )
        row = await cursor.fetchone()
        return row["data"] if row else None
