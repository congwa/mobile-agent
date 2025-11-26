#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iOS设备连接管理 - WebDriverAgent

功能：
1. 列出所有连接的iOS设备（模拟器和真机）
2. 连接指定设备
3. 检查设备状态
4. 管理WebDriverAgent服务


"""
import sys
import subprocess
import os
import json
from typing import List, Optional, Dict
from pathlib import Path


class IOSDeviceManager:
    """
    iOS设备连接管理器
    
    用法:
        manager = IOSDeviceManager()
        devices = manager.list_devices()
        driver = manager.connect(device_id="iPhone 15")
    """
    
    def __init__(self):
        """初始化iOS设备管理器"""
        self.xcrun_path = self._find_xcrun()
        self.driver = None
        self.current_device_id = None
    
    def _find_xcrun(self) -> str:
        """
        查找xcrun路径
        
        Returns:
            xcrun可执行文件路径
        """
        # xcrun通常在Xcode中，检查常见路径
        common_paths = [
            '/usr/bin/xcrun',
            '/usr/local/bin/xcrun',
        ]
        
        for path in common_paths:
            if Path(path).exists():
                return path
        
        # 尝试直接调用xcrun（可能在PATH中）
        try:
            result = subprocess.run(['xcrun', '--version'], capture_output=True, timeout=2)
            if result.returncode == 0:
                return 'xcrun'
        except:
            pass
        
        raise FileNotFoundError(
            "未找到xcrun，请安装Xcode Command Line Tools\n"
            "安装命令: xcode-select --install"
        )
    
    def list_devices(self) -> List[Dict[str, str]]:
        """
        列出所有可用的iOS设备（模拟器和真机）
        
        Returns:
            设备列表，每个设备包含id、name、type等信息
        """
        devices = []
        
        try:
            # 列出模拟器
            result = subprocess.run(
                [self.xcrun_path, 'simctl', 'list', 'devices', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                sim_data = json.loads(result.stdout)
                for runtime, sims in sim_data.get('devices', {}).items():
                    for sim in sims:
                        if sim.get('state') == 'Booted' or sim.get('isAvailable', False):
                            devices.append({
                                'id': sim.get('udid', ''),
                                'name': sim.get('name', 'Unknown'),
                                'type': 'simulator',
                                'runtime': runtime,
                                'state': sim.get('state', 'unknown')
                            })
            
            # 列出真机（通过idevice_id，需要libimobiledevice）
            try:
                result = subprocess.run(
                    ['idevice_id', '-l'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    for udid in result.stdout.strip().split('\n'):
                        if udid.strip():
                            devices.append({
                                'id': udid.strip(),
                                'name': 'iOS Device',
                                'type': 'device',
                                'state': 'connected'
                            })
            except FileNotFoundError:
                # libimobiledevice未安装，跳过真机检测
                pass
            
            return devices
            
        except subprocess.TimeoutExpired:
            raise RuntimeError("获取设备列表超时")
        except Exception as e:
            raise RuntimeError(f"获取设备列表失败: {e}")
    
    def connect(self, device_id: Optional[str] = None, use_webdriveragent: bool = True) -> 'webdriver.Remote':
        """
        连接iOS设备
        
        Args:
            device_id: 设备ID，None则自动选择第一个设备
            use_webdriveragent: 是否使用WebDriverAgent（默认True）
            
        Returns:
            WebDriver对象
        """
        if use_webdriveragent:
            return self._connect_with_webdriveragent(device_id)
        else:
            # 使用Appium（备选方案）
            return self._connect_with_appium(device_id)
    
    def _connect_with_webdriveragent(self, device_id: Optional[str] = None) -> 'webdriver.Remote':
        """使用WebDriverAgent连接"""
        try:
            from appium import webdriver
            from appium.options.ios import XCUITestOptions
            
            # 如果没有指定设备ID，自动选择第一个
            if device_id is None:
                devices = self.list_devices()
                if len(devices) == 0:
                    raise RuntimeError("未找到连接的设备，请连接设备后重试")
                device_id = devices[0]['id']
                print(f"📱 自动选择设备: {device_id}", file=sys.stderr)
            
            # 配置WebDriverAgent
            options = XCUITestOptions()
            options.platform_name = 'iOS'
            options.device_name = device_id
            options.automation_name = 'XCUITest'
            
            # WebDriverAgent默认端口
            wda_port = 8100
            
            # 连接WebDriverAgent
            self.driver = webdriver.Remote(
                f'http://localhost:{wda_port}',
                options=options
            )
            self.current_device_id = device_id
            
            print(f"✅ iOS设备连接成功: {device_id}", file=sys.stderr)
            
            return self.driver
            
        except ImportError:
            raise ImportError(
                "Appium未安装，请运行: pip install Appium-Python-Client\n"
                "iOS自动化还需要安装WebDriverAgent"
            )
        except Exception as e:
            raise RuntimeError(f"连接iOS设备失败: {e}\n"
                             f"请确保WebDriverAgent已启动: brew install ios-deploy\n"
                             f"然后运行: xcodebuild -project WebDriverAgent.xcodeproj -scheme WebDriverAgentRunner -destination 'id={device_id}' test")
    
    def _connect_with_appium(self, device_id: Optional[str] = None) -> 'webdriver.Remote':
        """使用Appium连接（备选方案）"""
        try:
            from appium import webdriver
            from appium.options.ios import XCUITestOptions
            
            if device_id is None:
                devices = self.list_devices()
                if len(devices) == 0:
                    raise RuntimeError("未找到连接的设备")
                device_id = devices[0]['id']
            
            options = XCUITestOptions()
            options.platform_name = 'iOS'
            options.device_name = device_id
            options.automation_name = 'XCUITest'
            
            # Appium Server默认端口
            self.driver = webdriver.Remote(
                'http://localhost:4723',
                options=options
            )
            self.current_device_id = device_id
            
            return self.driver
            
        except Exception as e:
            raise RuntimeError(f"Appium连接失败: {e}")
    
    def check_device_status(self) -> Dict[str, any]:
        """
        检查设备状态
        
        Returns:
            设备状态信息
        """
        if not self.driver:
            return {'connected': False, 'reason': '设备未连接'}
        
        try:
            # 获取设备信息
            capabilities = self.driver.capabilities
            return {
                'connected': True,
                'device_id': self.current_device_id,
                'platform_version': capabilities.get('platformVersion', 'Unknown'),
                'device_name': capabilities.get('deviceName', 'Unknown'),
            }
        except Exception as e:
            return {
                'connected': False,
                'reason': str(e)
            }
    
    def disconnect(self):
        """断开设备连接"""
        if self.driver:
            try:
                self.driver.quit()
            except:
                pass
        self.driver = None
        self.current_device_id = None
        print("📱 iOS设备已断开连接", file=sys.stderr)

