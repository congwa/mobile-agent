#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试操作历史记录功能

验证：
1. 操作历史是否被正确记录
2. 操作历史的success字段是否被正确更新
3. 能否基于操作历史生成测试脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mobile_mcp.core.mobile_client import MobileClient
from mobile_mcp.core.locator.mobile_smart_locator import MobileSmartLocator
from mobile_mcp.core.ai.test_generator_from_history import TestGeneratorFromHistory


async def test_operation_history():
    """测试操作历史记录"""
    print("=" * 60)
    print("🧪 测试操作历史记录功能")
    print("=" * 60)
    
    # 创建client
    client = MobileClient(device_id=None)
    
    # 启动应用
    print("\n📱 启动应用: com.im30.way")
    await client.launch_app("com.im30.way", wait_time=3)
    await asyncio.sleep(2)
    
    # 执行一些操作
    print("\n🔍 执行操作...")
    
    # 操作1: 点击底部第四个图标
    print("\n1. 点击底部第四个图标")
    try:
        result = await client.click("底部第四个图标", ref="[810,2186][1080,2356]", verify=False)
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   错误: {e}")
    
    await asyncio.sleep(1)
    
    # 操作2: 点击举报
    print("\n2. 点击举报")
    try:
        result = await client.click("举报", ref="[0,1333][1080,1460]", verify=False)
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   错误: {e}")
    
    await asyncio.sleep(1)
    
    # 操作3: 输入文本
    print("\n3. 输入文本")
    try:
        result = await client.type_text("输入框", "测试文本", ref="[81,292][999,826]")
        print(f"   结果: {result}")
    except Exception as e:
        print(f"   错误: {e}")
    
    await asyncio.sleep(1)
    
    # 检查操作历史
    print("\n" + "=" * 60)
    print("📋 操作历史记录")
    print("=" * 60)
    
    operation_history = getattr(client, 'operation_history', [])
    print(f"\n总操作数: {len(operation_history)}")
    
    for i, op in enumerate(operation_history, 1):
        print(f"\n操作 {i}:")
        print(f"  action: {op.get('action')}")
        print(f"  element: {op.get('element')}")
        print(f"  ref: {op.get('ref')}")
        print(f"  success: {op.get('success')}")
        if 'text' in op:
            print(f"  text: {op.get('text')}")
        if 'error' in op:
            print(f"  error: {op.get('error')}")
    
    # 筛选成功的操作
    successful_operations = [
        op for op in operation_history 
        if op.get('success', False)
    ]
    
    print(f"\n✅ 成功操作数: {len(successful_operations)}")
    
    # 尝试生成测试脚本
    if successful_operations:
        print("\n" + "=" * 60)
        print("📝 生成测试脚本")
        print("=" * 60)
        
        generator = TestGeneratorFromHistory(output_dir="tests")
        script = generator.generate_from_history(
            test_name="操作历史测试",
            package_name="com.im30.way",
            operation_history=successful_operations
        )
        
        script_path = generator.save("test_operation_history_generated", script)
        print(f"\n✅ 测试脚本已生成: {script_path}")
    else:
        print("\n⚠️  没有成功的操作，无法生成脚本")
    
    # 清理
    client.device_manager.disconnect()
    print("\n✅ 测试完成！")


if __name__ == "__main__":
    try:
        asyncio.run(test_operation_history())
    except KeyboardInterrupt:
        print("\n⚠️  已中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

