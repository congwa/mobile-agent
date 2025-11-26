#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
设备连接管理 - ADB设备管理

功能：
1. 列出所有连接的设备
2. 连接指定设备
3. 检查设备状态
4. 管理UIAutomator2服务
"""
import sys
import subprocess
import os
from typing import List, Optional, Dict
from pathlib import Path


class DeviceManager:
    """
    Android设备连接管理器
    
    用法:
        manager = DeviceManager()
        devices = manager.list_devices()
        u2 = manager.connect(device_id="emulator-5554")
    """
    
    def __init__(self, platform: str = "android"):
        """
        初始化设备管理器
        
        Args:
            platform: 平台类型 ("android" 或 "ios")
        """
        self.platform = platform
        if platform == "android":
            self.adb_path = self._find_adb()
            self.u2 = None
            self.current_device_id = None
        elif platform == "ios":
            # iOS设备管理器（延迟导入）
            from .ios_device_manager import IOSDeviceManager
            self.ios_manager = IOSDeviceManager()
            self.driver = None
            self.current_device_id = None
        else:
            raise ValueError(f"不支持的平台: {platform}")
    
    def _find_adb(self) -> str:
        """
        查找ADB路径
        
        Returns:
            ADB可执行文件路径
        """
        # 1. 检查环境变量
        adb_path = os.environ.get('ANDROID_HOME') or os.environ.get('ANDROID_SDK_ROOT')
        if adb_path:
            adb = Path(adb_path) / 'platform-tools' / 'adb'
            if adb.exists():
                return str(adb)
        
        # 2. 检查常见路径
        common_paths = [
            '/usr/local/bin/adb',
            '/usr/bin/adb',
            '~/Library/Android/sdk/platform-tools/adb',
            '~/Android/Sdk/platform-tools/adb',
            '~/Desktop/platform-tools/adb',  # 桌面上的platform-tools
        ]
        
        for path in common_paths:
            expanded = Path(path).expanduser()
            if expanded.exists():
                return str(expanded)
        
        # 3. 尝试直接调用adb（可能在PATH中）
        try:
            result = subprocess.run(['adb', 'version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                return 'adb'
        except:
            pass
        
        raise FileNotFoundError(
            "未找到ADB，请安装Android SDK Platform Tools\n"
            "下载地址: https://developer.android.com/studio/releases/platform-tools"
        )
    
    def list_devices(self) -> List[Dict[str, str]]:
        """
        列出所有连接的设备
        
        Returns:
            设备列表，每个设备包含id和状态
        """
        try:
            result = subprocess.run(
                [self.adb_path, "devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"ADB命令执行失败: {result.stderr}")
            
            devices = []
            for line in result.stdout.strip().split('\n')[1:]:  # 跳过第一行标题
                if line.strip():
                    parts = line.split('\t')
                    if len(parts) >= 2:
                        device_id = parts[0].strip()
                        status = parts[1].strip()
                        if status == 'device':  # 只返回已连接的设备
                            devices.append({
                                'id': device_id,
                                'status': status
                            })
            
            return devices
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("ADB命令超时，请检查设备连接")
        except Exception as e:
            raise RuntimeError(f"获取设备列表失败: {e}")
    
    def connect(self, device_id: Optional[str] = None) -> 'uiautomator2.Device':
        """
        连接设备
        
        Args:
            device_id: 设备ID，None则自动选择第一个设备
            
        Returns:
            UIAutomator2设备对象
        """
        try:
            import uiautomator2 as u2
        except ImportError:
            raise ImportError(
                "uiautomator2未安装，请运行: pip install uiautomator2\n"
                "安装后需要初始化: python -m uiautomator2 init"
            )
        
        # 如果没有指定设备ID，自动选择第一个
        if device_id is None:
            devices = self.list_devices()
            if len(devices) == 0:
                raise RuntimeError("未找到连接的设备，请连接设备后重试")
            device_id = devices[0]['id']
            print(f"📱 自动选择设备: {device_id}", file=sys.stderr)
        
        # 连接设备
        try:
            self.u2 = u2.connect(device_id)
            self.current_device_id = device_id
            
            # 检查设备信息
            info = self.u2.info
            print(f"✅ 设备连接成功: {device_id}", file=sys.stderr)
            print(f"   型号: {info.get('productName', 'Unknown')}", file=sys.stderr)
            print(f"   Android版本: {info.get('version', 'Unknown')}", file=sys.stderr)
            
            # 检查无障碍服务状态
            self._check_accessibility_service()
            
            return self.u2
            
        except Exception as e:
            raise RuntimeError(f"连接设备失败: {e}")
    
    def check_device_status(self) -> Dict[str, any]:
        """
        检查设备状态
        
        Returns:
            设备状态信息
        """
        if not self.u2:
            return {'connected': False, 'reason': '设备未连接'}
        
        try:
            info = self.u2.info
            return {
                'connected': True,
                'device_id': self.current_device_id,
                'product_name': info.get('productName', 'Unknown'),
                'version': info.get('version', 'Unknown'),
                'sdk': info.get('sdk', 0),
            }
        except Exception as e:
            return {
                'connected': False,
                'reason': str(e)
            }
    
    def _check_accessibility_service(self):
        """
        检查无障碍服务是否启用
        
        UIAutomator2需要无障碍服务才能正常工作
        ATX会自动安装并启用无障碍服务
        """
        if not self.u2:
            return
        
        try:
            # 尝试获取页面结构，如果失败可能是无障碍服务未启用
            xml = self.u2.dump_hierarchy()
            if xml and len(xml) > 100:  # 有内容说明无障碍服务正常
                print(f"   ✅ 无障碍服务: 已启用", file=sys.stderr)
                return
            
            print(f"   ⚠️  无障碍服务: 可能未启用", file=sys.stderr)
            print(f"   💡 提示: 如果定位失败，请检查是否启用了ATX的无障碍服务", file=sys.stderr)
            
        except Exception as e:
            print(f"   ⚠️  无障碍服务检查失败: {e}", file=sys.stderr)
            print(f"   💡 提示: 请确保已安装ATX并启用了无障碍服务", file=sys.stderr)
    
    def check_accessibility_service(self) -> Dict[str, any]:
        """
        检查无障碍服务状态（公开方法）
        
        Returns:
            无障碍服务状态信息
        """
        if not self.u2:
            return {
                'enabled': False,
                'reason': '设备未连接'
            }
        
        try:
            # 尝试获取页面结构
            xml = self.u2.dump_hierarchy()
            if xml and len(xml) > 100:
                return {
                    'enabled': True,
                    'message': '无障碍服务已启用'
                }
            else:
                return {
                    'enabled': False,
                    'reason': '无法获取页面结构，无障碍服务可能未启用',
                    'suggestion': '请检查是否启用了ATX的无障碍服务'
                }
        except Exception as e:
            return {
                'enabled': False,
                'reason': str(e),
                'suggestion': '请确保已安装ATX并启用了无障碍服务'
            }
    
    def disconnect(self):
        """断开设备连接"""
        self.u2 = None
        self.current_device_id = None
        print("📱 设备已断开连接", file=sys.stderr)

