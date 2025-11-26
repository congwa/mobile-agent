#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成独立的测试脚本 - 不依赖 mobile_mcp 包

生成纯粹基于 uiautomator2 的测试脚本，用户可以直接运行
"""
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class StandaloneTestGenerator:
    """
    生成独立的测试脚本（不依赖 mobile_mcp 包）
    
    特点：
    1. 只依赖 uiautomator2（用户常用库）
    2. 使用 MCP 验证过的坐标/bounds/resource-id
    3. 无需安装 mobile-mcp-ai 包即可运行
    """
    
    def __init__(self, output_dir: str = "./tests"):
        """
        初始化生成器
        
        Args:
            output_dir: 输出目录（默认为当前目录的tests子目录）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_from_history(
        self, 
        test_name: str, 
        package_name: str,
        operation_history: List[Dict],
        device_id: str = None
    ) -> str:
        """
        从操作历史生成独立的测试脚本
        
        Args:
            test_name: 测试用例名称
            package_name: App包名
            operation_history: 操作历史列表
            device_id: 设备ID（可选）
            
        Returns:
            生成的测试脚本内容
        """
        safe_name = re.sub(r'[^\w\s-]', '', test_name).strip().replace(' ', '_')
        
        # 生成脚本头部
        script_lines = self._generate_header(test_name, safe_name)
        
        # 生成导入部分
        script_lines.extend(self._generate_imports())
        
        # 生成常量
        script_lines.extend([
            f'PACKAGE_NAME = "{package_name}"',
            f'DEVICE_ID = {repr(device_id)}  # None表示自动选择第一个设备',
            "",
            ""
        ])
        
        # 生成 fixture
        script_lines.extend(self._generate_fixture())
        
        # 生成测试函数
        script_lines.extend(self._generate_test_function(
            test_name, safe_name, operation_history
        ))
        
        return "\n".join(script_lines)
    
    def _generate_header(self, test_name: str, safe_name: str) -> List[str]:
        """生成文件头部"""
        return [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            f'"""',
            f"移动端自动化测试: {test_name}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"依赖: pip install uiautomator2 pytest pytest-asyncio",
            f"",
            f"运行方式:",
            f"    pytest test_{safe_name}.py -v -s",
            f"    pytest test_{safe_name}.py --alluredir=./allure-results  # 生成allure报告",
            f'"""',
            ""
        ]
    
    def _generate_imports(self) -> List[str]:
        """生成导入部分"""
        return [
            "import time",
            "import pytest",
            "import uiautomator2 as u2",
            "",
            ""
        ]
    
    def _generate_fixture(self) -> List[str]:
        """生成 pytest fixture"""
        return [
            "@pytest.fixture(scope='function')",
            "def device():",
            '    """',
            "    pytest fixture: 创建并返回设备连接",
            "    scope='function': 每个测试函数都会创建一个新的连接",
            '    """',
            "    # 连接设备",
            "    d = u2.connect(DEVICE_ID)  # None表示自动选择第一个设备",
            "    print(f\"\\n📱 连接设备: {d.device_info}\")",
            "    ",
            "    # 启动App",
            "    print(f\"🚀 启动App: {PACKAGE_NAME}\")",
            "    d.app_start(PACKAGE_NAME, stop=True)",
            "    ",
            "    # 🎯 智能等待：App启动+首页加载（5-8秒）",
            "    print(\"⏳ 等待App启动和首页加载...\")",
            "    time.sleep(2)  # 等待进程启动",
            "    ",
            "    # 等待页面稳定（检测连续2次页面内容相同）",
            "    last_xml = None",
            "    stable_count = 0",
            "    max_wait = 8  # 最多等待8秒",
            "    start_time = time.time()",
            "    ",
            "    while time.time() - start_time < max_wait:",
            "        try:",
            "            current_xml = d.dump_hierarchy()",
            "            if current_xml == last_xml:",
            "                stable_count += 1",
            "                if stable_count >= 2:",
            "                    print(f\"✅ 首页加载完成（{time.time() - start_time:.1f}秒）\")",
            "                    break",
            "            else:",
            "                stable_count = 0",
            "            last_xml = current_xml",
            "            time.sleep(0.5)",
            "        except:",
            "            time.sleep(0.5)",
            "    ",
            "    yield d",
            "    ",
            "    # 清理（可选：关闭App）",
            "    # d.app_stop(PACKAGE_NAME)",
            "",
            ""
        ]
    
    def _generate_test_function(
        self, 
        test_name: str, 
        safe_name: str, 
        operations: List[Dict]
    ) -> List[str]:
        """生成测试函数"""
        lines = [
            f"def test_{safe_name.lower()}(device):",
            f'    """',
            f"    测试用例: {test_name}",
            f"    ",
            f"    Args:",
            f"        device: pytest fixture，已启动App的设备连接",
            f'    """',
            f"    d = device",
            f"    ",
        ]
        
        step_index = 1
        for op in operations:
            action = op.get('action')
            element = op.get('element', '')
            ref = op.get('ref', '')
            
            if action == 'click':
                lines.extend(self._generate_click_code(element, ref, step_index))
                step_index += 1
            elif action == 'type':
                text = op.get('text', '')
                lines.extend(self._generate_input_code(element, ref, text, step_index))
                step_index += 1
        
        # 添加断言（可选）
        lines.extend([
            "    ",
            "    # ✅ 测试完成",
            "    print(\"✅ 测试通过\")",
        ])
        
        return lines
    
    def _generate_click_code(self, element: str, ref: str, step: int) -> List[str]:
        """生成点击代码"""
        lines = [
            f"    # 步骤{step}: 点击 {element}",
            f"    print(f\"\\n步骤{step}: 点击 {element}\")",
        ]
        
        # 🎯 判断是否需要更长等待（页面跳转类操作）
        is_navigation = any(keyword in element.lower() for keyword in [
            '首页', '搜索', '返回', '确定', '提交', '登录', '注册', 
            'home', 'search', 'back', 'submit', 'login', 'register'
        ])
        wait_time = 2.0 if is_navigation else 1.5
        
        # 根据ref类型生成不同的点击代码
        if ref.startswith('[') and '][' in ref:
            # bounds坐标：[x1,y1][x2,y2]
            import re
            match = re.search(r'\[(\d+),(\d+)\]\[(\d+),(\d+)\]', ref)
            if match:
                x1, y1, x2, y2 = match.groups()
                x = (int(x1) + int(x2)) // 2
                y = (int(y1) + int(y2)) // 2
                lines.extend([
                    f"    d.click({x}, {y})  # 使用MCP验证过的坐标",
                    f"    time.sleep({wait_time})  # 等待页面响应",
                ])
        elif ref.startswith('com.') or ':id/' in ref:
            # resource-id
            lines.extend([
                f"    d(resourceId=\"{ref}\").click()  # 使用MCP验证过的resource-id",
                f"    time.sleep({wait_time})  # 等待页面响应",
            ])
        else:
            # text
            lines.extend([
                f"    d(text=\"{ref}\").click()  # 使用MCP验证过的text",
                f"    time.sleep({wait_time})  # 等待页面响应",
            ])
        
        lines.append("")
        return lines
    
    def _generate_input_code(self, element: str, ref: str, text: str, step: int) -> List[str]:
        """生成输入代码"""
        lines = [
            f"    # 步骤{step}: 在{element}输入 {text}",
            f"    print(f\"\\n步骤{step}: 在{element}输入 {text}\")",
        ]
        
        if ref.startswith('com.') or ':id/' in ref:
            # resource-id
            lines.extend([
                f"    d(resourceId=\"{ref}\").click()  # 先点击聚焦",
                f"    time.sleep(0.5)  # 等待键盘弹出",
                f"    d(resourceId=\"{ref}\").clear_text()  # 清空",
                f"    time.sleep(0.3)",
                f"    d(resourceId=\"{ref}\").set_text(\"{text}\")  # 输入",
                f"    time.sleep(1.5)  # 等待输入完成",
            ])
        else:
            # text
            lines.extend([
                f"    d(text=\"{ref}\").click()  # 先点击聚焦",
                f"    time.sleep(0.5)  # 等待键盘弹出",
                f"    d.clear_text()  # 清空",
                f"    time.sleep(0.3)",
                f"    d.send_keys(\"{text}\")  # 输入",
                f"    time.sleep(1.5)  # 等待输入完成",
            ])
        
        lines.append("")
        return lines
    
    def save(self, filename: str, script: str) -> Path:
        """
        保存脚本到文件
        
        Args:
            filename: 文件名（不含.py后缀）
            script: 脚本内容
            
        Returns:
            保存的文件路径
        """
        if not filename.endswith('.py'):
            filename = f"{filename}.py"
        
        file_path = self.output_dir / filename
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(script)
        
        print(f"✅ 测试用例已保存: {file_path}")
        return file_path

