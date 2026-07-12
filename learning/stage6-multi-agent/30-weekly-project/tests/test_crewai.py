"""
第 30 章 — CrewAI 流水线测试（真实框架版）

运行方式:  .venv/bin/python tests/test_crewai.py

测试 FR-1~FR-5 中 CrewAI 实现的部分。
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from common import check, get_or_create_llm, load_dotenv_if_needed, reset, section, summary

load_dotenv_if_needed()

from main import (  # noqa: E402
    classify_ticket,
    search_knowledge_base,
    generate_response,
    review_response,
    run_crewai_pipeline,
    get_crewai_llm,
)


def test_fr1_classify():
    """FR-1: 工单分类"""
    section("FR-1: 工单分类")

    llm = get_or_create_llm(temperature=0)
    test_cases = [
        ("我无法登录账号，一直提示密码错误", "technical"),
        ("我想申请退款，已经买了3天", "billing"),
        ("你们支持哪些语言", "general"),
    ]

    for question, expected_category in test_cases:
        try:
            result = classify_ticket(question, llm)
            check(
                f"「{question[:20]}...」→ {expected_category}",
                isinstance(result, dict) and result.get("category") == expected_category,
                detail=f"实际输出: {result}",
            )
        except NotImplementedError:
            check(
                f"「{question[:20]}...」→ {expected_category}", False, detail="TODO-FR-1 尚未实现"
            )
        except Exception as e:
            check(f"「{question[:20]}...」→ {expected_category}", False, detail=f"异常: {e}")


def test_fr2_search():
    """FR-2: 知识库检索"""
    section("FR-2: 知识库检索")

    llm = get_or_create_llm(temperature=0)

    try:
        results = search_knowledge_base("technical", "无法登录", llm)
        check("技术类查询返回结果", len(results) > 0)
        if results:
            check("结果标题与登录相关", any("登录" in r.get("title", "") for r in results))
    except NotImplementedError:
        check("技术类查询返回结果", False, detail="TODO-FR-2 尚未实现")
        check("结果标题与登录相关", False, detail="TODO-FR-2 尚未实现")

    try:
        empty_results = search_knowledge_base("billing", "量子力学问题", llm)
        check("无匹配查询返回空列表", len(empty_results) == 0)
    except NotImplementedError:
        check("无匹配查询返回空列表", False, detail="TODO-FR-2 尚未实现")


def test_fr3_generate():
    """FR-3: 回复生成"""
    section("FR-3: 回复生成")

    llm = get_or_create_llm(temperature=0)

    kb_results = [{"title": "登录问题排查", "content": "清除浏览器缓存和Cookie。检查SSO账号状态。"}]
    try:
        response = generate_response("我无法登录", "technical", kb_results, llm)
        check("生成了回复", bool(response))
        check(
            "回复长度适中 (50-500字)", 50 <= len(response) <= 500, detail=f"长度: {len(response)}"
        )
        check(
            "回复包含登录相关内容", "登录" in response or "缓存" in response or "密码" in response
        )
    except NotImplementedError:
        check("生成了回复", False, detail="TODO-FR-3 尚未实现")
        check("回复长度适中 (50-500字)", False, detail="TODO-FR-3 尚未实现")
        check("回复包含登录相关内容", False, detail="TODO-FR-3 尚未实现")

    # 边界：知识库为空
    try:
        honest_response = generate_response("量子计算机怎么用", "technical", [], llm)
        check(
            "知识库为空时诚实告知",
            any(kw in honest_response for kw in ["无法", "抱歉", "暂时", "不能", "没有"]),
            detail=f"回复: {honest_response[:100]}",
        )
    except NotImplementedError:
        check("知识库为空时诚实告知", False, detail="TODO-FR-3 尚未实现")


def test_fr4_review():
    """FR-4: 质量审核"""
    section("FR-4: 质量审核")

    llm = get_or_create_llm(temperature=0)

    good_response = (
        "您好，关于登录问题，建议您先清除浏览器缓存和 Cookie，"
        "然后检查 SSO 账号是否过期。如果问题仍然存在，请联系 IT 管理员重置密码。"
    )
    try:
        result = review_response("我无法登录", good_response, llm)
        check("审核结果包含 verdict", "verdict" in result)
        check("审核结果包含 feedback", "feedback" in result)
        check(
            "好回复应该 approved",
            result.get("verdict") == "approved",
            detail=f"verdict={result.get('verdict')}, feedback={result.get('feedback', '')[:80]}",
        )
    except NotImplementedError:
        check("审核结果包含 verdict", False, detail="TODO-FR-4 尚未实现")
        check("审核结果包含 feedback", False, detail="TODO-FR-4 尚未实现")
        check("好回复应该 approved", False, detail="TODO-FR-4 尚未实现")

    bad_response = "不知道，你自己看着办吧。"
    try:
        result_bad = review_response("我无法登录", bad_response, llm)
        check(
            "差回复应该 rejected",
            result_bad.get("verdict") == "rejected",
            detail=f"verdict={result_bad.get('verdict')}, feedback={result_bad.get('feedback', '')[:80]}",
        )
    except NotImplementedError:
        check("差回复应该 rejected", False, detail="TODO-FR-4 尚未实现")


def test_crewai_llm_config():
    """验证 CrewAI LLM 配置可用"""
    section("CrewAI LLM 配置")

    try:
        crewai_llm = get_crewai_llm()
        check("get_crewai_llm 返回 LLM 实例", crewai_llm is not None)
        check("LLM 有 model 属性", hasattr(crewai_llm, "model"))
        print(f"  CrewAI LLM model: {crewai_llm.model}")
    except NotImplementedError:
        check("get_crewai_llm 返回 LLM 实例", False, detail="TODO-CREWAI-LLM 尚未实现")
        check("LLM 有 model 属性", False, detail="TODO-CREWAI-LLM 尚未实现")
    except Exception as e:
        check("get_crewai_llm 返回 LLM 实例", False, detail=f"异常: {e}")
        check("LLM 有 model 属性", False, detail=f"异常: {e}")


def test_fr5_crewai_pipeline():
    """FR-5a: CrewAI 完整流水线"""
    section("FR-5a: CrewAI 完整流水线（真实框架）")

    try:
        result = run_crewai_pipeline("我无法登录账号")
        check("流水线返回 dict", isinstance(result, dict))
        check("包含 final_response", bool(result.get("final_response")))
        check("包含 category 字段", "category" in result)
        check("category 为 technical", result.get("category") == "technical")
        check("包含 review_verdict 字段", "review_verdict" in result)

        # 审核通过时 pipeline 应为 crewai
        check("pipeline 标识为 crewai", result.get("pipeline") == "crewai")
    except NotImplementedError:
        for label in [
            "流水线返回 dict",
            "包含 final_response",
            "包含 category 字段",
            "category 为 technical",
            "包含 review_verdict 字段",
            "pipeline 标识为 crewai",
        ]:
            check(label, False, detail="TODO-FR-5a 尚未实现")
    except Exception as e:
        check("流水线返回 dict", False, detail=f"异常: {e}")

    # 测试不同输入类型
    try:
        result_billing = run_crewai_pipeline("怎么退款")
        check("账单类问题分类正确", result_billing.get("category") == "billing")
    except NotImplementedError:
        check("账单类问题分类正确", False, detail="TODO-FR-5a 尚未实现")


if __name__ == "__main__":
    reset()
    test_fr1_classify()
    test_fr2_search()
    test_fr3_generate()
    test_fr4_review()
    test_crewai_llm_config()
    test_fr5_crewai_pipeline()
    summary()
