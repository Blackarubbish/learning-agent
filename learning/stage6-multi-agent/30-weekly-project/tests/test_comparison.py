"""
第 30 章 — 框架对比分析测试

运行方式:  .venv/bin/python tests/test_comparison.py

测试 compare_frameworks 的完整性和深度。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import check, reset, section, summary

from main import compare_frameworks  # noqa: E402


def test_comparison_completeness():
    """验证框架对比包含 4 个必要维度"""
    section("框架对比: 维度完整性")

    try:
        result = compare_frameworks()
        check("compare_frameworks 返回 dict", isinstance(result, dict))
    except NotImplementedError:
        for label in [
            "compare_frameworks 返回 dict", "包含代码结构维度", "包含可观测性维度",
            "包含灵活性维度", "包含选型建议维度",
        ]:
            check(label, False, detail="TODO-COMPARE 尚未实现")
        for label in ["代码结构分析非空", "可观测性分析非空", "灵活性分析非空", "选型建议非空"]:
            check(label, False, detail="TODO-COMPARE 尚未实现")
        return

    required_dimensions = {
        "代码结构": "CrewAI vs LangGraph 代码组织差异",
        "可观测性": "哪个更容易追踪中间状态",
        "灵活性": "流程变更时哪个更容易调整",
        "选型建议": "什么场景推荐用哪种",
    }

    for dim_key in required_dimensions:
        # 精确匹配或模糊匹配
        matched_key = None
        for key in result:
            if dim_key in key:
                matched_key = key
                break
        if matched_key is None:
            # 尝试英文/相似匹配
            for key in result:
                if any(w in key for w in ["代码", "结构", "组织", "code"]):
                    if dim_key == "代码结构":
                        matched_key = key
                        break
                if any(w in key for w in ["观测", "调试", "debug", "trace", "observ"]):
                    if dim_key == "可观测性":
                        matched_key = key
                        break
                if any(w in key for w in ["灵活", "flexib", "变更"]):
                    if dim_key == "灵活性":
                        matched_key = key
                        break
                if any(w in key for w in ["选型", "选择", "推荐", "场景"]):
                    if dim_key == "选型建议":
                        matched_key = key
                        break

        if matched_key:
            content = str(result[matched_key])
            check(f"包含「{dim_key}」维度: {matched_key}", True)
            check(
                f"「{dim_key}」分析非空且有意义 (>=20字)",
                len(content) >= 20,
                detail=f"内容长度: {len(content)}",
            )
        else:
            check(f"包含「{dim_key}」维度", False, detail=f"现有维度: {list(result.keys())}")


def test_comparison_insight():
    """验证分析包含具体技术判断"""
    section("框架对比: 分析深度")

    try:
        result = compare_frameworks()
    except NotImplementedError:
        check("分析提到框架名称", False, detail="TODO-COMPARE 尚未实现")
        check("分析包含具体场景", False, detail="TODO-COMPARE 尚未实现")
        check("有明确选型结论", False, detail="TODO-COMPARE 尚未实现")
        return

    all_text = " ".join(str(v) for v in result.values())

    # 必须提到至少 2 个框架名（真实框架版应该提到 CrewAI 和 LangGraph）
    fw_count = sum(
        1 for fw in ["CrewAI", "LangGraph", "StateGraph", "Crew", "langgraph", "crewai"]
        if fw.lower() in all_text.lower()
    )
    check("分析提到至少 2 个框架名", fw_count >= 2, detail=f"提到 {fw_count} 个")

    # 必须包含具体场景描述
    scenario_keywords = ["客服", "工单", "流水线", "状态机", "审批", "退回", "路由", "审核"]
    scenario_count = sum(1 for kw in scenario_keywords if kw.lower() in all_text.lower())
    check("分析包含具体场景描述", scenario_count >= 1, detail=f"场景关键词: {scenario_count} 个")

    # 必须有明确选型建议
    rec_keywords = ["推荐", "建议", "适合", "场景", "选择", "用"]
    rec_count = sum(1 for kw in rec_keywords if kw.lower() in all_text.lower())
    check("选型建议有明确结论", rec_count >= 1, detail=f"建议关键词: {rec_count} 个")

    # 额外：应体现对真实框架 API 的体验
    api_keywords = ["API", "kickoff", "invoke", "compile", "llm", "context", "StateGraph"]
    api_count = sum(1 for kw in api_keywords if kw.lower() in all_text.lower())
    check("分析体现真实 API 使用体验", api_count >= 2, detail=f"API 关键词: {api_count} 个")


if __name__ == "__main__":
    reset()
    test_comparison_completeness()
    test_comparison_insight()
    summary()
