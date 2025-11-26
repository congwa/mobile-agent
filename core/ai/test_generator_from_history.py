#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
基于操作历史生成测试脚本 - 智能定位 + 自动降级

功能：
1. 从操作历史（operation_history）生成脚本
2. 优先使用MCP验证过的定位方式（快速、准确）
3. 定位失败时自动降级到智能定位（自愈能力）
4. 页面改版后大部分用例能自动适应

用法:
    generator = TestGeneratorFromHistory()
    script = generator.generate_from_history(
        test_name="测试用例",
        package_name="com.im30.way",
        operation_history=client.operation_history
    )
    generator.save("test_generated.py", script)
"""
import sys
import re
from pathlib import Path
from typing import List, Dict
from datetime import datetime


class TestGeneratorFromHistory:
    """
    基于操作历史生成测试脚本
    
    特点：
    - 优先使用MCP验证过的定位方式（性能最优）
    - 定位失败时自动降级到智能定位（自愈能力）
    - 页面改版后大部分用例能自动适应
    """
    
    def __init__(self, output_dir: str = "tests"):
        """
        初始化生成器
        
        Args:
            output_dir: 生成的测试文件输出目录（默认tests，用于pytest）
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(exist_ok=True)
        
        # 🎯 弹窗关键词（用于识别可选操作）
        self.popup_keywords = [
            "允许", "取消", "确定", "同意", "拒绝", "关闭", "跳过", 
            "知道了", "我知道了", "好的", "稍后", "暂不", "以后再说",
            "Allow", "Cancel", "OK", "Agree", "Deny", "Close", "Skip",
            "Got it", "Later", "Not now"
        ]
        
        # 🎯 弹窗resource-id特征
        self.popup_id_patterns = ["permission", "dialog", "alert", "popup", "grant"]
    
    def _is_popup_element(self, element: str, ref: str) -> bool:
        """
        判断是否是弹窗元素（可选操作）
        
        Args:
            element: 元素描述
            ref: 元素定位方式
            
        Returns:
            True表示是弹窗元素
        """
        # 检查元素描述是否包含弹窗关键词
        for keyword in self.popup_keywords:
            if keyword in element:
                return True
        
        # 检查resource-id是否包含弹窗特征
        ref_lower = ref.lower()
        for pattern in self.popup_id_patterns:
            if pattern in ref_lower:
                return True
        
        return False
    
    def _is_dropdown_scenario(self, operations: List[Dict], index: int) -> bool:
        """
        判断是否是下拉框场景
        
        Args:
            operations: 操作历史列表
            index: 当前操作的索引
            
        Returns:
            True表示当前操作是下拉框选择的第二步（需要等待）
        """
        # 检查：当前是click，且前一个也是click
        if index > 0:
            current = operations[index]
            previous = operations[index - 1]
            
            if current.get('action') == 'click' and previous.get('action') == 'click':
                current_element = current.get('element', '')
                
                # 🎯 排除明显的按钮关键词
                button_keywords = ["按钮", "button", "btn", "继续", "下一步", "跳过", "完成"]
                for keyword in button_keywords:
                    if keyword in current_element.lower():
                        return False
                
                # 🎯 选项通常是1-5个字符（排除按钮后）
                # 例如："北京"(2)、"男"(1)、"确定"(2)、"China"(5)
                if 1 <= len(current_element) <= 5:
                    return True
        
        return False
    
    def generate_from_history(
        self, 
        test_name: str, 
        package_name: str,
        operation_history: List[Dict]
    ) -> str:
        """
        从操作历史生成测试脚本
        
        Args:
            test_name: 测试用例名称
            package_name: App包名
            operation_history: 操作历史列表
            
        Returns:
            生成的测试脚本内容
        """
        # 生成文件名（中文转拼音或直接使用）
        safe_name = re.sub(r'[^\w\s-]', '', test_name).strip().replace(' ', '_')
        
        # 生成脚本内容（pytest格式）
        script_lines = [
            "#!/usr/bin/env python3",
            "# -*- coding: utf-8 -*-",
            f'"""',
            f"移动端测试用例: {test_name}",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"",
            f"✨ 特性：智能定位 + 自动降级",
            f"   - 优先使用MCP验证过的定位方式（快速）",
            f"   - 定位失败时自动降级到智能定位（自愈）",
            f"   - 页面改版后大部分用例能自动适应",
            f"",
            f"运行方式:",
            f"    pytest {safe_name}.py -v",
            f"    pytest {safe_name}.py --alluredir=./allure-results  # 生成allure报告",
            f'"""',
            "import asyncio",
            "import pytest",
            "import sys",
            "from pathlib import Path",
            "",
            "# 添加backend目录到路径",
            "# tests目录结构: backend/mobile_mcp/tests/test_xxx.py",
            "# 需要导入: backend/mobile_mcp/core/mobile_client.py",
            "sys.path.insert(0, str(Path(__file__).parent.parent))",
            "",
            "from mobile_mcp.core.mobile_client import MobileClient",
            "from mobile_mcp.core.locator.mobile_smart_locator import MobileSmartLocator",
            "",
            "",
            f"PACKAGE_NAME = \"{package_name}\"",
            "",
            "",
            "@pytest.fixture(scope='function')",
            "async def mobile_client():",
            "    \"\"\"",
            "    pytest fixture: 创建并返回MobileClient实例",
            "    scope='function': 每个测试函数都会创建一个新的client",
            "    \"\"\"",
            "    client = MobileClient(device_id=None)",
            "    ",
            "    # 🎯 附加智能定位器（用于降级场景）",
            "    client.smart_locator = MobileSmartLocator(client)",
            "    ",
            "    # 启动App",
            "    print(f\"\\n📱 启动App: {{PACKAGE_NAME}}\", file=sys.stderr)",
            "    result = await client.launch_app(PACKAGE_NAME, wait_time=5)",
            "    if not result.get('success'):",
            "        raise Exception(f\"启动App失败: {{result.get('reason')}}\")",
            "    ",
            "    await asyncio.sleep(2)  # 等待页面加载",
            "    ",
            "    yield client",
            "    ",
            "    # 清理",
            "    client.device_manager.disconnect()",
            "",
            "",
            f"@pytest.mark.asyncio",
            f"async def test_{safe_name.lower()}(mobile_client):",
            f'    """',
            f"    测试用例: {test_name}",
            f"    ",
            f"    Args:",
            f"        mobile_client: pytest fixture，已启动App的MobileClient实例",
            f'    """',
            f"    client = mobile_client",
            f"    ",
            f"    print(\"=\" * 60, file=sys.stderr)",
            f"    print(f\"🚀 {test_name}\", file=sys.stderr)",
            f"    print(\"=\" * 60, file=sys.stderr)",
            f"    ",
            f"    try:",
        ]
        
        # 根据操作历史生成测试步骤
        step_index = 1
        for op_index, operation in enumerate(operation_history):
            action = operation.get('action')
            element = operation.get('element', '')
            ref = operation.get('ref', '')
            
            if action == 'click':
                # 🎯 判断是否是弹窗元素（可选操作）
                is_popup = self._is_popup_element(element, ref)
                
                script_lines.append(f"        # 步骤{step_index}: 点击 {element}")
                script_lines.append(f"        print(f\"\\n步骤{step_index}: 点击 {element}\", file=sys.stderr)")
                
                # 🎯 弹窗元素：可选操作（不出现也不报错）
                if is_popup:
                    script_lines.append(f"        # 🎯 可选操作：弹窗/权限请求（不一定出现）")
                    script_lines.append(f"        try:")
                else:
                    script_lines.append(f"        try:")
                
                # 根据ref类型生成不同的优先定位代码
                if ref.startswith('vision_coord_'):
                    # 视觉识别坐标：vision_coord_x_y
                    parts = ref.replace('vision_coord_', '').split('_')
                    if len(parts) >= 2:
                        x, y = parts[0], parts[1]
                        script_lines.append(f"            # 优先使用MCP验证过的坐标")
                        script_lines.append(f"            client.u2.click({x}, {y})")
                        script_lines.append(f"            print(f\"✅ 点击成功（坐标: {x}, {y}）\", file=sys.stderr)")
                elif ref.startswith('[') and '][' in ref:
                    # bounds坐标：[x1,y1][x2,y2]
                    script_lines.append(f"            # 优先使用MCP验证过的bounds")
                    script_lines.append(f"            await client.click(\"{element}\", ref=\"{ref}\", verify=False)")
                    script_lines.append(f"            print(f\"✅ 点击成功（bounds: {ref}）\", file=sys.stderr)")
                elif ref.startswith('com.') or ':' in ref:
                    # resource-id定位
                    script_lines.append(f"            # 优先使用MCP验证过的resource-id")
                    script_lines.append(f"            await client.click(\"{element}\", ref=\"{ref}\", verify=False)")
                    script_lines.append(f"            print(f\"✅ 点击成功（resource-id: {ref}）\", file=sys.stderr)")
                else:
                    # text/description定位
                    script_lines.append(f"            # 优先使用MCP验证过的text/description")
                    script_lines.append(f"            await client.click(\"{element}\", ref=\"{ref}\", verify=False)")
                    script_lines.append(f"            print(f\"✅ 点击成功（text: {ref}）\", file=sys.stderr)")
                
                # 添加降级逻辑（区分弹窗和普通元素）
                if is_popup:
                    # 🎯 弹窗：失败不报错，只打印提示
                    script_lines.append(f"        except Exception as e:")
                    script_lines.append(f"            # 弹窗未出现，跳过")
                    script_lines.append(f"            print(f\"ℹ️  '{element}'未出现，跳过（可能已授权或无需操作）\", file=sys.stderr)")
                else:
                    # 🎯 普通元素：失败后启用智能定位
                    script_lines.append(f"        except Exception as e:")
                    script_lines.append(f"            # 🎯 原定位失效，启用智能定位（自愈）")
                    script_lines.append(f"            print(f\"⚠️  原定位失效: {{e}}\", file=sys.stderr)")
                    script_lines.append(f"            print(f\"🔍 启用智能定位重新查找'{element}'...\", file=sys.stderr)")
                    script_lines.append(f"            ")
                    script_lines.append(f"            locate_result = await client.smart_locator.locate(\"{element}\")")
                    script_lines.append(f"            if locate_result:")
                    script_lines.append(f"                await client.click(\"{element}\", ref=locate_result['ref'], verify=False)")
                    script_lines.append(f"                print(f\"✅ 智能定位成功: {{locate_result['ref']}}\", file=sys.stderr)")
                    script_lines.append(f"            else:")
                    script_lines.append(f"                raise Exception(f\"❌ 智能定位也失败了，元素'{element}'可能已被删除或页面结构大幅改变\")")
                script_lines.append(f"        ")
                
                # 🎯 下拉框场景：添加等待
                if self._is_dropdown_scenario(operation_history, op_index):
                    script_lines.append(f"        await asyncio.sleep(0.5)  # 🎯 等待下拉选项加载")
                else:
                    script_lines.append(f"        await asyncio.sleep(1.5)  # 等待页面响应")
                
                step_index += 1
            
            elif action == 'type':
                text = operation.get('text', '')
                script_lines.append(f"        # 步骤{step_index}: 在{element}输入 {text}")
                script_lines.append(f"        print(f\"\\n步骤{step_index}: 在{element}输入 {text}\", file=sys.stderr)")
                
                # 🎯 生成智能定位 + 自动降级代码
                script_lines.append(f"        try:")
                
                # 🎯 输入前先清空（避免内容累加）
                script_lines.append(f"            # 🎯 先点击输入框聚焦")
                if ref.startswith('[') and '][' in ref:
                    script_lines.append(f"            await client.click(\"{element}\", ref=\"{ref}\", verify=False)")
                elif ref.startswith('com.') or ':' in ref:
                    script_lines.append(f"            await client.click(\"{element}\", ref=\"{ref}\", verify=False)")
                else:
                    script_lines.append(f"            await client.click(\"{element}\", ref=\"{ref}\", verify=False)")
                
                script_lines.append(f"            await asyncio.sleep(0.3)")
                script_lines.append(f"            ")
                script_lines.append(f"            # 🎯 清空输入框（避免内容累加）")
                script_lines.append(f"            if client.platform == 'android':")
                script_lines.append(f"                client.u2.clear_text()")
                script_lines.append(f"            elif client.platform == 'ios':")
                script_lines.append(f"                # iOS清空逻辑")
                script_lines.append(f"                pass")
                script_lines.append(f"            await asyncio.sleep(0.2)")
                script_lines.append(f"            ")
                
                # 根据ref类型生成不同的优先定位代码
                if ref.startswith('[') and '][' in ref:
                    # bounds坐标
                    script_lines.append(f"            # 优先使用MCP验证过的bounds")
                    script_lines.append(f"            await client.type_text(\"{element}\", \"{text}\", ref=\"{ref}\")")
                    script_lines.append(f"            print(f\"✅ 输入成功（bounds: {ref}）\", file=sys.stderr)")
                elif ref.startswith('com.') or ':' in ref:
                    # resource-id定位
                    script_lines.append(f"            # 优先使用MCP验证过的resource-id")
                    script_lines.append(f"            await client.type_text(\"{element}\", \"{text}\", ref=\"{ref}\")")
                    script_lines.append(f"            print(f\"✅ 输入成功（resource-id: {ref}）\", file=sys.stderr)")
                else:
                    # text定位
                    script_lines.append(f"            # 优先使用MCP验证过的text")
                    script_lines.append(f"            await client.type_text(\"{element}\", \"{text}\", ref=\"{ref}\")")
                    script_lines.append(f"            print(f\"✅ 输入成功（text: {ref}）\", file=sys.stderr)")
                
                # 添加降级逻辑
                script_lines.append(f"        except Exception as e:")
                script_lines.append(f"            # 🎯 原定位失效，启用智能定位（自愈）")
                script_lines.append(f"            print(f\"⚠️  原定位失效: {{e}}\", file=sys.stderr)")
                script_lines.append(f"            print(f\"🔍 启用智能定位重新查找'{element}'...\", file=sys.stderr)")
                script_lines.append(f"            ")
                script_lines.append(f"            locate_result = await client.smart_locator.locate(\"{element}\")")
                script_lines.append(f"            if locate_result:")
                script_lines.append(f"                # 重新点击聚焦")
                script_lines.append(f"                await client.click(\"{element}\", ref=locate_result['ref'], verify=False)")
                script_lines.append(f"                await asyncio.sleep(0.3)")
                script_lines.append(f"                # 清空")
                script_lines.append(f"                if client.platform == 'android':")
                script_lines.append(f"                    client.u2.clear_text()")
                script_lines.append(f"                await asyncio.sleep(0.2)")
                script_lines.append(f"                # 输入")
                script_lines.append(f"                await client.type_text(\"{element}\", \"{text}\", ref=locate_result['ref'])")
                script_lines.append(f"                print(f\"✅ 智能定位成功: {{locate_result['ref']}}\", file=sys.stderr)")
                script_lines.append(f"            else:")
                script_lines.append(f"                raise Exception(f\"❌ 智能定位也失败了，元素'{element}'可能已被删除或页面结构大幅改变\")")
                script_lines.append(f"        ")
                script_lines.append(f"        await asyncio.sleep(1)  # 等待输入完成")
                
                step_index += 1
        
        # 添加结尾（pytest格式）
        script_lines.extend([
            f"        ",
            f"        print(\"\\n✅ 测试完成！\", file=sys.stderr)",
            f"        ",
            f"    except AssertionError as e:",
            f"        print(f\"\\n❌ 断言失败: {{e}}\", file=sys.stderr)",
            f"        # 打印当前页面快照以便调试",
            f"        snapshot = await client.snapshot()",
            f"        print(f\"\\n当前页面快照:\\n{{snapshot[:500]}}...\", file=sys.stderr)",
            f"        raise",
            f"    except Exception as e:",
            f"        print(f\"\\n❌ 测试失败: {{e}}\", file=sys.stderr)",
            f"        import traceback",
            f"        traceback.print_exc()",
            f"        raise",
        ])
        
        return '\n'.join(script_lines)
    
    def save(self, filename: str, script: str):
        """
        保存生成的测试脚本
        
        Args:
            filename: 文件名（会自动添加.py后缀）
            script: 脚本内容
        """
        if not filename.endswith('.py'):
            filename += '.py'
        
        file_path = self.output_dir / filename
        file_path.write_text(script, encoding='utf-8')
        print(f"✅ 测试用例已保存: {file_path}", file=sys.stderr)
        return file_path

