"""测试所有 API 端点（不启动 MCP/Agent，仅验证路由和 schema）

使用临时 SQLite 数据库文件进行测试。
"""

from __future__ import annotations

import asyncio
import os
import tempfile

import pytest
from fastapi.testclient import TestClient

from mobile_agent.core.service import MobileAgentService


@pytest.fixture(autouse=True)
def _reset_singleton():
    """每个测试前重置单例"""
    MobileAgentService._instance = None
    yield
    MobileAgentService._instance = None


@pytest.fixture
def _init_storage():
    """初始化 Storage（使用临时数据库文件）"""
    from mobile_agent.core.service import get_agent_service

    service = get_agent_service()
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    asyncio.get_event_loop().run_until_complete(service._storage.init(db_path))
    yield service
    asyncio.get_event_loop().run_until_complete(service._storage.close())
    os.unlink(db_path)


@pytest.fixture
def client(_init_storage):
    """创建测试客户端（跳过 lifespan 初始化，但 Storage 已就绪）"""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    from mobile_agent.api.chat import router as chat_router
    from mobile_agent.api.conversations import router as conversations_router
    from mobile_agent.api.devices import router as devices_router
    from mobile_agent.api.settings import router as settings_router

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(chat_router)
    app.include_router(devices_router)
    app.include_router(conversations_router)
    app.include_router(settings_router)

    return TestClient(app)


# ── Status ────────────────────────────────────────────────────


class TestStatus:
    def test_status_not_ready(self, client: TestClient):
        """未初始化时 status 返回 not ready"""
        resp = client.get("/api/v1/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ready"] is False
        assert data["mcp_connected"] is False
        assert data["tools_count"] == 0
        assert data["tool_names"] == []
        assert "tools" in data
        assert "uptime_seconds" in data


# ── Screenshot ────────────────────────────────────────────────


class TestScreenshot:
    def test_screenshot_not_found(self, client: TestClient):
        """请求不存在的截图返回 404"""
        resp = client.get("/api/v1/screenshot/nonexistent-id")
        assert resp.status_code == 404

    def test_screenshot_store_and_get(self, client: TestClient):
        """存储并获取截图"""
        from mobile_agent.core.service import get_agent_service

        service = get_agent_service()
        # 存储一个简单的 base64 PNG（1x1 红色像素）
        png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        sid = asyncio.get_event_loop().run_until_complete(
            service.store_screenshot(png_b64)
        )
        assert sid

        resp = client.get(f"/api/v1/screenshot/{sid}")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert len(resp.content) > 0


# ── Devices ───────────────────────────────────────────────────


class TestDevices:
    def test_list_devices_empty(self, client: TestClient):
        """未初始化时设备列表为空"""
        resp = client.get("/api/v1/devices")
        assert resp.status_code == 200
        data = resp.json()
        assert data["devices"] == []


# ── Conversations ─────────────────────────────────────────────


class TestConversations:
    def test_list_empty(self, client: TestClient):
        """初始状态会话列表为空"""
        resp = client.get("/api/v1/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["conversations"] == []
        assert data["total"] == 0

    def test_crud_conversation(self, client: TestClient):
        """会话 CRUD 流程"""
        from mobile_agent.core.service import get_agent_service

        service = get_agent_service()
        loop = asyncio.get_event_loop()

        # 创建会话
        loop.run_until_complete(
            service.save_conversation(
                "conv-1",
                "测试会话",
                status="success",
                steps=2,
                duration="3s",
            )
        )
        # 添加消息
        loop.run_until_complete(
            service.add_message("conv-1", "user", "你好")
        )
        loop.run_until_complete(
            service.add_message("conv-1", "assistant", "你好！")
        )

        # 列表
        resp = client.get("/api/v1/conversations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["conversations"][0]["id"] == "conv-1"

        # 搜索
        resp = client.get("/api/v1/conversations?query=测试")
        assert resp.json()["total"] == 1

        resp = client.get("/api/v1/conversations?query=不存在")
        assert resp.json()["total"] == 0

        # 详情
        resp = client.get("/api/v1/conversations/conv-1")
        assert resp.status_code == 200
        detail = resp.json()
        assert detail["id"] == "conv-1"
        assert len(detail["messages"]) == 2

        # 404
        resp = client.get("/api/v1/conversations/nonexistent")
        assert resp.status_code == 404

        # 删除
        resp = client.delete("/api/v1/conversations/conv-1")
        assert resp.status_code == 200

        resp = client.get("/api/v1/conversations")
        assert resp.json()["total"] == 0

        # 重复删除 404
        resp = client.delete("/api/v1/conversations/conv-1")
        assert resp.status_code == 404


# ── Settings ──────────────────────────────────────────────────


class TestSettings:
    def test_get_settings(self, client: TestClient):
        """获取设置"""
        resp = client.get("/api/v1/settings")
        assert resp.status_code == 200
        data = resp.json()
        assert "llm" in data
        assert "mcp" in data
        assert "agent" in data
        assert "middleware" in data
        assert "model" in data["llm"]

    def test_update_settings(self, client: TestClient):
        """更新设置"""
        resp = client.put(
            "/api/v1/settings",
            json={
                "agent": {"max_iterations": 30},
                "middleware": {"retry": False},
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent"]["max_iterations"] == 30
        assert data["middleware"]["retry"] is False

    def test_update_llm_model(self, client: TestClient):
        """更新 LLM 模型"""
        resp = client.put(
            "/api/v1/settings",
            json={"llm": {"model": "anthropic:claude-3.5-sonnet"}},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["llm"]["model"] == "anthropic:claude-3.5-sonnet"


# ── Service 单元测试 ──────────────────────────────────────────


class TestServiceUnit:
    def test_mask_key(self):
        """API Key 遮蔽"""
        from mobile_agent.core.service import _mask_key

        assert _mask_key("") == "***"
        assert _mask_key("short") == "***"
        result = _mask_key("sk-1234567890abcdef")
        assert result.startswith("sk-1")
        assert result.endswith("cdef")
        assert "*" in result

    def test_screenshot_cache_limit(self, _init_storage):
        """截图存储上限（保留最近 50 张）"""
        from mobile_agent.core.service import get_agent_service

        service = get_agent_service()
        loop = asyncio.get_event_loop()
        for i in range(60):
            loop.run_until_complete(service.store_screenshot(f"data_{i}"))

        # 验证 SQLite 中只保留了 50 张
        cursor = loop.run_until_complete(
            service._storage._db.execute("SELECT count(*) FROM screenshots")
        )
        row = loop.run_until_complete(cursor.fetchone())
        assert row[0] == 50

    def test_conversation_operations(self, _init_storage):
        """会话操作"""
        from mobile_agent.core.service import get_agent_service

        service = get_agent_service()
        loop = asyncio.get_event_loop()

        loop.run_until_complete(service.save_conversation("c1", "会话1"))
        loop.run_until_complete(service.save_conversation("c2", "会话2"))

        convs = loop.run_until_complete(service.list_conversations())
        assert len(convs) == 2

        assert loop.run_until_complete(service.get_conversation("c1")) is not None
        assert loop.run_until_complete(service.get_conversation("c999")) is None

        assert loop.run_until_complete(service.delete_conversation("c1")) is True
        assert loop.run_until_complete(service.delete_conversation("c1")) is False
        convs = loop.run_until_complete(service.list_conversations())
        assert len(convs) == 1

    def test_settings_snapshot(self):
        """设置快照"""
        from mobile_agent.core.service import get_agent_service

        service = get_agent_service()
        snap = service.get_settings_snapshot()
        assert "llm" in snap
        assert "mcp" in snap
        assert "agent" in snap
        assert "middleware" in snap

    def test_update_settings(self):
        """更新设置"""
        from mobile_agent.core.service import get_agent_service

        service = get_agent_service()
        result = service.update_settings({
            "middleware": {"retry": False, "retry_max_attempts": 5},
        })
        assert result["middleware"]["retry"] is False
        assert result["middleware"]["retry_max_attempts"] == 5


# ── Storage 单元测试 ──────────────────────────────────────────


class TestStorage:
    def test_storage_init_and_close(self):
        """Storage 初始化和关闭"""
        from mobile_agent.core.storage import Storage

        storage = Storage()
        loop = asyncio.get_event_loop()

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        loop.run_until_complete(storage.init(db_path))
        assert storage.is_initialized

        loop.run_until_complete(storage.close())
        assert not storage.is_initialized
        os.unlink(db_path)

    def test_message_auto_creates_conversation(self):
        """添加消息时自动创建会话"""
        from mobile_agent.core.storage import Storage

        storage = Storage()
        loop = asyncio.get_event_loop()

        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        loop.run_until_complete(storage.init(db_path))

        # 直接添加消息到不存在的会话
        loop.run_until_complete(
            storage.add_message("auto-conv", "user", "你好世界")
        )

        # 会话应该自动创建
        conv = loop.run_until_complete(storage.get_conversation("auto-conv"))
        assert conv is not None
        assert len(conv["messages"]) == 1

        loop.run_until_complete(storage.close())
        os.unlink(db_path)
