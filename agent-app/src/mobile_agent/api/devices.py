"""设备管理端点"""

from __future__ import annotations

from fastapi import APIRouter

from mobile_agent.api.schemas import DeviceInfo, DeviceListResponse
from mobile_agent.core.service import get_agent_service

router = APIRouter(prefix="/api/v1", tags=["devices"])


@router.get("/devices", response_model=DeviceListResponse)
async def list_devices():
    """获取设备列表

    通过 MCP Server 的 mobile_list_devices 工具获取真实设备信息。
    """
    service = get_agent_service()

    raw_devices = await service.get_devices()
    devices = [
        DeviceInfo(
            id=d.get("id", "unknown"),
            name=d.get("name", "Mobile Device"),
            platform=d.get("platform", "Android"),
            version=d.get("version", ""),
            resolution=d.get("resolution", ""),
            connected=d.get("connected", True),
        )
        for d in raw_devices
    ]

    return DeviceListResponse(devices=devices)
