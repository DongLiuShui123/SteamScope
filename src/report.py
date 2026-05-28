import pandas as pd


def build_product_report(result: dict, game_info: dict | None = None) -> str:
    summary = result["summary"]
    keyword_df: pd.DataFrame = result["keywords"]
    pain_df: pd.DataFrame = result["pain_points"]

    top_keywords = keyword_df["关键词"].head(8).tolist()
    top_keyword_text = "、".join(top_keywords) or "暂无"
    main_pain = _main_pain(pain_df)
    mood = _judge_mood(summary["ai_positive_rate"], summary["ai_negative_rate"])
    risk = _judge_risk(summary["ai_negative_rate"], main_pain["命中次数"])
    conclusion = _build_conclusion(summary, main_pain, mood, risk)

    title = f"## 《{game_info['name']}》玩家情绪分析报告\n\n" if game_info else ""

    return f"""
{title}## 一、总览

| 指标 | 结果 |
|---|---:|
{_game_row(game_info)}
| 有效评论 | {summary['total_reviews']} 条 |
| 已过滤无效评论 | {summary.get('filtered_invalid_reviews', 0)} 条 |
| Steam 好评率 | {summary['steam_positive_rate']:.1%} |
| AI 正向率 | {summary['ai_positive_rate']:.1%} |
| AI 负向率 | {summary['ai_negative_rate']:.1%} |
| 口碑风险 | {risk} |

**结论：** {conclusion}

## 二、核心发现

- **玩家满意点：** 重点观察 `{top_keyword_text}` 等高频词，可用于提炼玩法、角色、剧情或体验卖点。
- **玩家不满点：** 当前负反馈最集中在 **{main_pain['问题类型']}**，命中 **{main_pain['命中次数']}** 次。
- **社区热点：** 高频讨论词可作为社区公告、攻略内容、问卷和活动选题入口。

## 三、问题优先级

{_priority_table(summary['ai_negative_rate'], pain_df)}

## 四、运营建议

- **版本运营：** 优先复核高频负面问题，将影响进入游戏、游玩流畅度、联机稳定性或退款意愿的问题进入近期排期。
- **社区运营：** 对高赞差评和争议评论进行人工复核，必要时发布问题收集帖、进度说明或 FAQ。
- **内容运营：** 放大玩家高频正向词和安利评论，转化为攻略、角色话题、截图征集或二创活动。
- **数据监控：** 持续观察好评率、负向率、差评关键词、情绪趋势、评论量和高赞差评变化。

## 五、典型评论

**正向反馈**

{_format_examples(result.get("positive_examples", []), limit=2)}

**负向反馈**

{_format_examples(result.get("negative_examples", []), limit=2)}

**安利/争议评论**

{_format_examples(_mixed_examples(result), limit=2)}
"""


def _main_pain(pain_df: pd.DataFrame) -> dict:
    if pain_df.empty:
        return {"问题类型": "暂无明显聚类", "命中次数": 0, "相关词": "暂无"}
    return pain_df.iloc[0].to_dict()


def _priority_table(negative_rate: float, pain_df: pd.DataFrame) -> str:
    rows = []
    for index, (_, row) in enumerate(pain_df.head(3).iterrows()):
        if row["命中次数"] <= 0:
            continue
        priority = "高" if index == 0 and (negative_rate >= 0.3 or row["命中次数"] >= 10) else "中"
        action = _action_for_pain(row["问题类型"])
        evidence = f"命中 {row['命中次数']} 次；相关词：{row['相关词']}"
        rows.append((priority, row["问题类型"], evidence, action))

    if not rows:
        rows.append(("低", "暂无集中问题", "未发现明显负面聚类", "保持常规监控"))

    table = ["| 优先级 | 问题类型 | 数据证据 | 建议动作 |", "|---|---|---|---|"]
    table.extend(f"| {priority} | {issue} | {evidence} | {action} |" for priority, issue, evidence, action in rows)
    return "\n".join(table)


def _action_for_pain(issue: str) -> str:
    actions = {
        "性能优化": "进入版本修复排期，更新后重点观察差评关键词是否下降",
        "内容体验": "补充玩家调研，判断是内容不足、重复感还是难度问题",
        "付费与价格": "复核价格、DLC、折扣期反馈，避免商业化口碑风险扩大",
        "联机与社区": "排查服务器、匹配、外挂和联机稳定性，并及时社区回应",
        "新手引导": "补充教程、FAQ、攻略入口，降低新手流失",
    }
    return actions.get(issue, "复核原文并持续监控")


def _build_conclusion(summary: dict, main_pain: dict, mood: str, risk: str) -> str:
    return (
        f"当前玩家情绪{mood}，口碑风险为 **{risk}**。"
        f"负反馈主要集中在 **{main_pain['问题类型']}**，建议优先结合原文复核，"
        "并在版本迭代、社区回应和内容运营中同步跟进。"
    )


def _judge_mood(positive_rate: float, negative_rate: float) -> str:
    if positive_rate >= 0.65 and negative_rate <= 0.25:
        return "整体偏正向"
    if negative_rate >= 0.45:
        return "整体偏负向"
    return "较为分化"


def _judge_risk(negative_rate: float, pain_count: int) -> str:
    if negative_rate >= 0.5 or pain_count >= 40:
        return "高"
    if negative_rate >= 0.3 or pain_count >= 15:
        return "中"
    return "低"


def _format_examples(examples: list[str], limit: int = 2) -> str:
    if not examples:
        return "- 暂无典型样例"
    return "\n".join(f"- {text[:150]}{'...' if len(text) > 150 else ''}" for text in examples[:limit])


def _mixed_examples(result: dict) -> list[str]:
    return result.get("strong_positive_examples", []) + result.get("review_needed_examples", [])


def _game_row(game_info: dict | None) -> str:
    if not game_info:
        return ""
    return f"| 游戏名称 | {game_info['name']} |\n"
