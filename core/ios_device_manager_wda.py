#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
iOS设备连接管理 - 使用 tidevice + facebook-wda

优势：
1. API风格和 uiautomator2 几乎一样
2. 不需要启动 Appium Server
3. tidevice 简化设备管理

前置条件：
1. 安装 tidevice: pip install tidevice
2. 安装 facebook-wda: pip install facebook-wda
3. 首次需要用 Xcode 编译 WebDriverAgent 到设备上

用法:
    manager = IOSDeviceManagerWDA()
    devices = manager.list_devices()
    client = manager.connect(device_id="xxx")
    client(text="登录").click()  # 和 uiautomator2 风格一样！
"""
import sys
import subprocess
from typing import List, Optional, Dict


class IOSDeviceManagerWDA:
    """
    iOS设备管理器 - 使用 tidevice + facebook-wda
    
    用法:
        manager = IOSDeviceManagerWDA()
        devices = manager.list_devices()
        client = manager.connect()
        client(text="登录").click()
    """
    
    def __init__(self):
        """初始化iOS设备管理器"""
        self.client = None
        self.current_device_id = None
        self._wda_proxy_process = None
        self._check_dependencies()
    
    def _check_dependencies(self):
        """检查依赖是否安装"""
        try:
            import tidevice
            import wda
        except ImportError as e:
            raise ImportError(
                f"缺少iOS自动化依赖: {e}\n"
                f"请运行以下命令安装:\n"
                f"  pip install tidevice facebook-wda\n"
            )
    
    def list_devices(self) -> List[Dict[str, str]]:
        """
        列出所有连接的iOS设备
        
        Returns:
            设备列表，每个设备包含 id, name, type 等信息
        """
        devices = []
        
        try:
            # 优先使用 tidevice Python API
            try:
                import tidevice
                for d in tidevice.Usbmux().device_list():
                    devices.append({
                        'id': d.udid,
                        'name': d.name if hasattr(d, 'name') else 'iOS Device',
                        'type': 'device',
                        'state': 'connected'
                    })
                if devices:
                    return devices
            except Exception:
                pass
            
            # 回退：使用 subprocess 调用 tidevice
            result = subprocess.run(
                [sys.executable, '-m', 'tidevice', 'list', '--json'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                import json
                try:
                    device_list = json.loads(result.stdout)
                    for device in device_list:
                        devices.append({
                            'id': device.get('udid', ''),
                            'name': device.get('name', 'iOS Device'),
                            'type': 'device',
                            'model': device.get('model', 'Unknown'),
                            'ios_version': device.get('version', 'Unknown'),
                            'state': 'connected'
                        })
                except json.JSONDecodeError:
                    # 尝试纯文本解析
                    for line in result.stdout.strip().split('\n'):
                        if line.strip():
                            parts = line.split()
                            if len(parts) >= 1:
                                devices.append({
                                    'id': parts[0],
                                    'name': ' '.join(parts[1:]) if len(parts) > 1 else 'iOS Device',
                                    'type': 'device',
                                    'state': 'connected'
                                })
            
            # 如果 tidevice 没有找到设备，尝试使用 xcrun simctl 列出模拟器
            if not devices:
                sim_result = subprocess.run(
                    ['xcrun', 'simctl', 'list', 'devices', 'booted', '--json'],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if sim_result.returncode == 0 and sim_result.stdout.strip():
                    import json
                    sim_data = json.loads(sim_result.stdout)
                    for runtime, sims in sim_data.get('devices', {}).items():
                        for sim in sims:
                            if sim.get('state') == 'Booted':
                                devices.append({
                                    'id': sim.get('udid', ''),
                                    'name': sim.get('name', 'Simulator'),
                                    'type': 'simulator',
                                    'runtime': runtime,
                                    'state': 'Booted'
                                })
            
            return devices
            
        except FileNotFoundError:
            print("⚠️  tidevice 未安装，请运行: pip install tidevice", file=sys.stderr)
            return []
        except Exception as e:
            print(f"⚠️  获取设备列表失败: {e}", file=sys.stderr)
            return []
    
    def start_wda_proxy(self, device_id: str, port: int = 8100) -> bool:
        """
        启动 WDA 代理（如果尚未启动）
        
        Args:
            device_id: 设备UDID
            port: WDA代理端口，默认8100
            
        Returns:
            是否成功启动
        """
        try:
            import socket
            
            # 检查端口是否已被占用（可能WDA已在运行）
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', port))
            sock.close()
            
            if result == 0:
                print(f"  ✅ WDA代理已在运行 (端口 {port})", file=sys.stderr)
                return True
            
            # 启动 WDA 代理
            print(f"  🚀 启动 WDA 代理...", file=sys.stderr)
            
            # 使用 tidevice 启动 WDA（后台运行）
            self._wda_proxy_process = subprocess.Popen(
                [sys.executable, '-m', 'tidevice', '-u', device_id, 'wdaproxy', '-B', 
                 'com.facebook.WebDriverAgentRunner.xctrunner', '--port', str(port)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            
            # 等待 WDA 启动
            import time
            for i in range(10):  # 最多等待10秒
                time.sleep(1)
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                result = sock.connect_ex(('localhost', port))
                sock.close()
                
                if result == 0:
                    print(f"  ✅ WDA代理启动成功 (端口 {port})", file=sys.stderr)
                    return True
                    
                print(f"  ⏳ 等待WDA启动... ({i+1}/10)", file=sys.stderr)
            
            print(f"  ❌ WDA代理启动超时", file=sys.stderr)
            return False
            
        except Exception as e:
            print(f"  ❌ 启动WDA代理失败: {e}", file=sys.stderr)
            return False
    
    def connect(self, device_id: Optional[str] = None, port: int = 8100) -> 'wda.Client':
        """
        连接iOS设备
        
        Args:
            device_id: 设备UDID，None则自动选择第一个设备
            port: WDA代理端口，默认8100
            
        Returns:
            wda.Client 对象（API类似 uiautomator2）
        """
        try:
            import wda
            
            # 如果没有指定设备ID，自动选择第一个
            if device_id is None:
                devices = self.list_devices()
                if not devices:
                    raise RuntimeError(
                        "未找到连接的iOS设备\n"
                        "请确保:\n"
                        "1. iOS设备已通过USB连接\n"
                        "2. 设备已信任此电脑\n"
                        "3. tidevice已安装: pip install tidevice"
                    )
                device_id = devices[0]['id']
                print(f"  📱 自动选择设备: {device_id}", file=sys.stderr)
            
            self.current_device_id = device_id
            
            # 尝试启动 WDA 代理
            self.start_wda_proxy(device_id, port)
            
            # 连接到 WDA
            self.client = wda.Client(f'http://localhost:{port}')
            
            # 测试连接
            try:
                status = self.client.status()
                print(f"  ✅ iOS设备连接成功: {device_id}", file=sys.stderr)
                print(f"     iOS版本: {status.get('os', {}).get('version', 'Unknown')}", file=sys.stderr)
            except Exception as e:
                print(f"  ⚠️  连接可能不稳定: {e}", file=sys.stderr)
            
            return self.client
            
        except ImportError:
            raise ImportError(
                "facebook-wda 未安装\n"
                "请运行: pip install facebook-wda"
            )
        except Exception as e:
            error_msg = str(e)
            if "Connection refused" in error_msg:
                raise RuntimeError(
                    f"无法连接到WDA (端口 {port})\n"
                    f"请确保:\n"
                    f"1. WebDriverAgent 已安装到设备上（需要用Xcode首次编译）\n"
                    f"2. 运行: tidevice -u {device_id} wdaproxy -B com.facebook.WebDriverAgentRunner.xctrunner\n"
                    f"3. 或者检查端口 {port} 是否被占用"
                )
            raise RuntimeError(f"连接iOS设备失败: {e}")
    
    def check_device_status(self) -> Dict:
        """
        检查设备连接状态
        
        Returns:
            设备状态信息
        """
        if not self.client:
            return {'connected': False, 'reason': '设备未连接'}
        
        try:
            status = self.client.status()
            return {
                'connected': True,
                'device_id': self.current_device_id,
                'ios_version': status.get('os', {}).get('version', 'Unknown'),
                'wda_version': status.get('build', {}).get('productBundleIdentifier', 'Unknown'),
            }
        except Exception as e:
            return {
                'connected': False,
                'reason': str(e)
            }
    
    def disconnect(self):
        """断开设备连接"""
        if self._wda_proxy_process:
            try:
                self._wda_proxy_process.terminate()
                self._wda_proxy_process.wait(timeout=5)
            except:
                pass
            self._wda_proxy_process = None
        
        self.client = None
        self.current_device_id = None
        print("  📱 iOS设备已断开连接", file=sys.stderr)




