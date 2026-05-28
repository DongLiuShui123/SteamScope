from collections import Counter
import re

import jieba
import pandas as pd
from snownlp import SnowNLP


STOPWORDS = {
    "游戏",
    "一个",
    "真的",
    "感觉",
    "还是",
    "就是",
    "这个",
    "没有",
    "不是",
    "可以",
    "非常",
    "比较",
    "玩家",
    "时候",
    "已经",
    "因为",
    "但是",
    "如果",
    "自己",
    "什么",
    "有点",
    "一下",
    "还有",
    "the",
    "and",
    "game",
    "this",
    "that",
}


PAIN_POINT_RULES = {
    "性能优化": ["优化", "卡顿", "掉帧", "帧数", "闪退", "崩溃", "加载", "bug", "BUG"],
    "内容体验": ["剧情", "任务", "地图", "关卡", "玩法", "重复", "无聊", "难度"],
    "付费与价格": ["价格", "贵", "打折", "DLC", "付费", "退款", "性价比"],
    "联机与社区": ["联机", "服务器", "匹配", "网络", "好友", "外挂", "作弊"],
    "新手引导": ["教程", "引导", "看不懂", "上手", "说明", "新手"],
}


GAME_POSITIVE_WORDS = {
    "萌",
    "好磕",
    "美味",
    "小甜饼",
    "甜饼",
    "对胃口",
    "爽",
    "上头",
    "喜欢",
    "可爱",
    "友好",
    "值",
    "推荐",
    "快来",
    "全通",
    "神作",
    "好玩",
    "香",
    "厨力",
    "满意",
    "优秀",
    "不错",
}


GAME_NEGATIVE_WORDS = {
    "退款",
    "差评",
    "失望",
    "优化差",
    "闪退",
    "卡顿",
    "bug",
    "BUG",
    "倒霉",
    "素质",
    "无聊",
    "不推荐",
    "崩溃",
    "恶心",
    "服了",
    "难受",
    "差劲",
    "垃圾",
}


PLAYFUL_WORDS = {
    "卧槽",
    "毒舌",
    "玩弄",
    "不萌",
    "骨科",
    "伪骨科",
    "属性",
}


INVALID_REVIEW_PATTERNS = [
    "看看我下面",
    "下面的强烈推荐",
    "可以看看我",
    "点我主页",
    "看我主页",
    "欢迎加群",
    "QQ群",
    "折扣群",
    "淘宝",
    "店铺",
    "代购",
    "求互赞",
]


def analyze_reviews(raw_reviews: list[dict]) -> dict:
    reviews = [_normalize_review(item) for item in raw_reviews]
    df = pd.DataFrame(reviews)
    df = df.dropna(subset=["review"]).drop_duplicates(subset=["review"])
    df = df[df["review"].str.strip().str.len() > 0].copy()

    df["clean_review"] = df["review"].apply(_clean_text)
    before_filter_count = len(df)
    df["is_valid_review"] = df["clean_review"].apply(_is_valid_review)
    df["invalid_reason"] = df["clean_review"].apply(_invalid_reason)
    df = df[df["is_valid_review"]].copy()
    filtered_count = before_filter_count - len(df)

    if df.empty:
        raise RuntimeError("过滤无效评论后没有可分析内容，请调整筛选条件或关闭部分过滤规则。")

    df["snownlp_score"] = df["clean_review"].apply(_sentiment_score)
    sentiment_result = df.apply(_hybrid_sentiment, axis=1, result_type="expand")
    df["sentiment_score"] = sentiment_result["sentiment_score"]
    df["sentiment_label"] = sentiment_result["sentiment_label"]
    df["sentiment_type"] = sentiment_result["sentiment_type"]
    df["sentiment_reason"] = sentiment_result["sentiment_reason"]
    df["created_date"] = pd.to_datetime(df["created_at"], unit="s", errors="coerce").dt.date
    df["playtime_hours"] = (df["playtime_forever"] / 60).round(1)

    keywords = extract_keywords(df["clean_review"].tolist(), top_n=20)
    pain_points = detect_pain_points(df)

    total = len(df)
    positive_count = int((df["sentiment_label"] == "正向").sum())
    negative_count = int((df["sentiment_label"] == "负向").sum())
    steam_positive_count = int(df["voted_up"].sum())

    summary = {
        "total_reviews": total,
        "steam_positive_rate": steam_positive_count / total if total else 0,
        "ai_positive_rate": positive_count / total if total else 0,
        "ai_negative_rate": negative_count / total if total else 0,
        "avg_sentiment_score": float(df["sentiment_score"].mean()) if total else 0,
        "avg_playtime_hours": float(df["playtime_hours"].mean()) if total else 0,
        "filtered_invalid_reviews": filtered_count,
    }

    return {
        "reviews": df,
        "keywords": pd.DataFrame(keywords, columns=["关键词", "出现次数"]),
        "pain_points": pain_points,
        "summary": summary,
        "positive_examples": _examples(df, "正向"),
        "negative_examples": _examples(df, "负向"),
        "strong_positive_examples": _examples_by_type(df, "高强度安利"),
        "review_needed_examples": _review_needed_examples(df),
    }


def extract_keywords(texts: list[str], top_n: int = 20) -> list[tuple[str, int]]:
    words: list[str] = []
    for text in texts:
        for word in jieba.cut(text):
            word = word.strip()
            if len(word) < 2:
                continue
            if word in STOPWORDS:
                continue
            if re.fullmatch(r"[0-9a-zA-Z_]+", word) and len(word) < 4:
                continue
            words.append(word)
    return Counter(words).most_common(top_n)


def detect_pain_points(df: pd.DataFrame) -> pd.DataFrame:
    negative_text = "\n".join(df.loc[df["sentiment_label"] == "负向", "clean_review"].tolist())
    rows = []
    for category, words in PAIN_POINT_RULES.items():
        count = sum(negative_text.count(word) for word in words)
        rows.append({"问题类型": category, "命中次数": count, "相关词": "、".join(words[:5])})
    return pd.DataFrame(rows).sort_values("命中次数", ascending=False)


def _normalize_review(item: dict) -> dict:
    author = item.get("author", {})
    return {
        "review": item.get("review", ""),
        "voted_up": bool(item.get("voted_up")),
        "votes_up": item.get("votes_up", 0),
        "votes_funny": item.get("votes_funny", 0),
        "weighted_vote_score": item.get("weighted_vote_score", "0"),
        "created_at": item.get("timestamp_created"),
        "playtime_forever": author.get("playtime_forever", 0),
        "steamid": author.get("steamid", ""),
    }


def _clean_text(text: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(text))
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _is_valid_review(text: str) -> bool:
    return _invalid_reason(text) == ""


def _invalid_reason(text: str) -> str:
    if len(text.strip()) < 4:
        return "内容过短"

    if any(pattern in text for pattern in INVALID_REVIEW_PATTERNS):
        return "疑似广告或导流"

    colon_count = text.count("：") + text.count(":")
    has_recommend_words = "推荐" in text or "强烈推荐" in text
    has_many_titles = colon_count >= 3 and len(text) >= 80
    adult_ad_words = ["黄油", "色情", "PORN", "Orgasm", "妓院"]
    adult_ad_hits = sum(text.count(word) for word in adult_ad_words)

    if has_recommend_words and has_many_titles:
        return "疑似跨游戏推荐清单"

    if adult_ad_hits >= 2 and has_many_titles:
        return "疑似黄油广告清单"

    return ""


def _sentiment_score(text: str) -> float:
    if not text:
        return 0.5
    try:
        return float(SnowNLP(text[:500]).sentiments)
    except Exception:
        return 0.5


def _sentiment_label(score: float) -> str:
    if score >= 0.6:
        return "正向"
    if score <= 0.4:
        return "负向"
    return "中性"


def _hybrid_sentiment(row: pd.Series) -> dict:
    text = row["clean_review"]
    snownlp_score = row["snownlp_score"]
    voted_up = bool(row["voted_up"])
    base_label = _sentiment_label(snownlp_score)
    positive_hits = _count_hits(text, GAME_POSITIVE_WORDS)
    negative_hits = _count_hits(text, GAME_NEGATIVE_WORDS)
    playful_hits = _count_hits(text, PLAYFUL_WORDS)
    is_enthusiastic = _is_enthusiastic_positive(text, positive_hits, playful_hits)

    if voted_up and base_label == "负向":
        if is_enthusiastic or positive_hits >= 2:
            return {
                "sentiment_score": max(snownlp_score, 0.68),
                "sentiment_label": "正向",
                "sentiment_type": "高强度安利",
                "sentiment_reason": "Steam 推荐，且命中游戏圈正向/玩梗表达",
            }
        if negative_hits >= 3:
            return {
                "sentiment_score": 0.55,
                "sentiment_label": "中性",
                "sentiment_type": "推荐但含负面表达",
                "sentiment_reason": "Steam 推荐，但文本含较多真实负面词，建议人工复核",
            }
        return {
            "sentiment_score": 0.62,
            "sentiment_label": "正向",
            "sentiment_type": "争议正向",
            "sentiment_reason": "Steam 推荐优先，SnowNLP 可能受口语或玩梗词影响",
        }

    if not voted_up and base_label == "正向":
        return {
            "sentiment_score": min(snownlp_score, 0.38),
            "sentiment_label": "负向",
            "sentiment_type": "争议负向",
            "sentiment_reason": "Steam 不推荐优先，文本可能含反讽或先扬后抑",
        }

    if voted_up and is_enthusiastic:
        return {
            "sentiment_score": max(snownlp_score, 0.72),
            "sentiment_label": "正向",
            "sentiment_type": "高强度安利",
            "sentiment_reason": "命中强烈安利表达",
        }

    return {
        "sentiment_score": snownlp_score,
        "sentiment_label": base_label,
        "sentiment_type": "常规" + base_label,
        "sentiment_reason": "按 SnowNLP 情感分数判断",
    }


def _count_hits(text: str, words: set[str]) -> int:
    return sum(text.count(word) for word in words)


def _is_enthusiastic_positive(text: str, positive_hits: int, playful_hits: int) -> bool:
    exclamation_count = text.count("!") + text.count("！")
    repeated_phrase = bool(re.search(r"(.{2,12})\1{2,}", text))
    return positive_hits >= 2 and (exclamation_count >= 2 or repeated_phrase or playful_hits >= 1)


def _examples(df: pd.DataFrame, label: str, limit: int = 3) -> list[str]:
    if label == "正向":
        sample = df[df["sentiment_label"] == label].sort_values("sentiment_score", ascending=False)
    else:
        sample = df[df["sentiment_label"] == label].sort_values("sentiment_score", ascending=True)
    return sample["clean_review"].head(limit).tolist()


def _examples_by_type(df: pd.DataFrame, type_keyword: str, limit: int = 3) -> list[str]:
    sample = df[df["sentiment_type"].str.contains(type_keyword, na=False)]
    sample = sample.sort_values("sentiment_score", ascending=False)
    return sample["clean_review"].head(limit).tolist()


def _review_needed_examples(df: pd.DataFrame, limit: int = 3) -> list[str]:
    sample = df[df["sentiment_type"].str.contains("争议|复核|含负面", regex=True, na=False)]
    sample = sample.sort_values("votes_up", ascending=False)
    return sample["clean_review"].head(limit).tolist()
