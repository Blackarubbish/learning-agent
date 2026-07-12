"""
自检工具 — 在每个练习末尾添加断言，即时获得反馈

用法：
    from common import check

    # 简单断言
    check("检索结果数量", len(results) == 3, f"期望 3 个，实际 {len(results)}")

    # 带自动修复提示
    check("向量维度", dim == 768, "请检查 Embedding 模型配置", fix="修改 DIMENSION 为 768")

    # 在末尾打印总结
    from common import section
    section("3. 混合检索测试")
"""

import sys

_checks_passed = 0
_checks_failed = 0
_current_section = ""


def section(title: str):
    """
    打印章节标题，用于组织输出。
    使用后自动打印分隔线和标题。
    """
    global _current_section
    _current_section = title
    print(f"\n{'─' * 50}")
    print(f"  {title}")
    print(f"{'─' * 50}")


def check(name: str, condition: bool, detail: str = "", fix: str = ""):
    """
    执行一项自检。

    Args:
        name: 检查项名称
        condition: 条件表达式
        detail: 失败时的详细说明
        fix: 修复建议

    Returns:
        bool: 是否通过
    """
    global _checks_passed, _checks_failed

    if condition:
        _checks_passed += 1
        print(f"  ✅ {name}")
        return True
    else:
        _checks_failed += 1
        print(f"  ❌ {name} 失败: {detail}")
        if fix:
            print(f"     💡 修复建议: {fix}")
        return False


def summary():
    """打印所有自检的总结"""
    total = _checks_passed + _checks_failed
    if total == 0:
        print("\n⚠️  没有注册任何自检项")
        return

    print(f"\n{'=' * 50}")
    if _checks_failed == 0:
        print(f"  🎉 全部通过！({_checks_passed}/{total})")
    else:
        print(f"  ⚠️  通过 {_checks_passed}/{total}，失败 {_checks_failed}/{total}")
    print(f"{'=' * 50}\n")


def reset():
    """重置计数器（每个脚本开始时调用）"""
    global _checks_passed, _checks_failed
    _checks_passed = 0
    _checks_failed = 0
