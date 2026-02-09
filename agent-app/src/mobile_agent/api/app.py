"""FastAPI 应用入口"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from mobile_agent.api.chat import router as chat_router
from mobile_agent.api.conversations import router as conversations_router
from mobile_agent.api.devices import router as devices_router
from mobile_agent.api.settings import router as settings_router
from mobile_agent.core.config import get_settings
from mobile_agent.core.service import get_agent_service

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    settings = get_settings()
    service = get_agent_service()

    logger.info("正在初始化 Agent 服务...")
    try:
        await service.initialize(settings)
        logger.info("Agent 服务初始化完成")
    except Exception as e:
        logger.error("Agent 服务初始化失败: %s", e)
        raise

    yield

    logger.info("正在关闭 Agent 服务...")
    await service.shutdown()
    logger.info("Agent 服务已关闭")


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="Mobile Agent API",
        description="基于 langchain.agents + langgraph-agent-kit 的移动端自动化 Agent",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # 注册路由
    app.include_router(chat_router)
    app.include_router(devices_router)
    app.include_router(conversations_router)
    app.include_router(settings_router)

    return app


app = create_app()
