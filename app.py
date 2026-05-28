from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import analyze_reviews
from src.report import build_product_report
from src.steam_api import fetch_game_details, fetch_steam_reviews


st.set_page_config(
    page_title="SteamScope - AI 游戏评论洞察系统",
    page_icon="🎮",
    layout="wide",
)

st.markdown(
    """
    <style>
    .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1180px;
    }
    h1 {
        letter-spacing: 0;
        margin-bottom: 0.25rem;
    }
    h2, h3 {
        letter-spacing: 0;
    }
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e8edf3;
        border-radius: 8px;
        padding: 14px 16px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    div[data-testid="stMetricLabel"] {
        color: #667085;
    }
    div[data-testid="stMetricValue"] {
        color: #101828;
        font-size: 1.45rem;
    }
    .section-note {
        color: #667085;
        font-size: 0.92rem;
        margin-top: -0.35rem;
        margin-bottom: 0.75rem;
    }
    .report-card {
        background: #ffffff;
        border: 1px solid #e8edf3;
        border-radius: 8px;
        padding: 20px 22px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
    }
    .report-card h2 {
        font-size: 1.15rem;
        margin-top: 1.1rem;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid #eef2f6;
    }
    .report-card h2:first-child {
        margin-top: 0;
    }
    .report-card h3 {
        font-size: 1rem;
        margin-top: 0.9rem;
    }
    .report-card table {
        font-size: 0.92rem;
    }
    .game-summary {
        border: 1px solid #e8edf3;
        border-radius: 8px;
        padding: 16px 18px;
        margin: 0.5rem 0 1rem;
        background: #f8fbff;
    }
    .game-title {
        font-size: 1.25rem;
        font-weight: 700;
        color: #101828;
        margin-bottom: 0.35rem;
    }
    .game-meta {
        color: #667085;
        font-size: 0.92rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


st.title("SteamScope - AI 游戏评论洞察系统")
st.caption("输入 Steam AppID，自动采集玩家评论，生成情绪、关键词和产品运营建议。")


with st.sidebar:
    st.header("分析设置")
    app_id = st.text_input("Steam AppID", value="1245620", help="例如：1245620 是 Elden Ring")
    max_reviews = st.slider("评论数量", min_value=100, max_value=2000, value=500, step=100)
    language = st.selectbox(
        "评论语言",
        options=[
            ("schinese", "简体中文"),
            ("english", "英文"),
            ("all", "全部"),
        ],
        format_func=lambda item: item[1],
    )
    review_type = st.selectbox(
        "评论类型",
        options=[
            ("all", "全部"),
            ("positive", "仅好评"),
            ("negative", "仅差评"),
        ],
        format_func=lambda item: item[1],
    )
    run_button = st.button("开始分析", type="primary", use_container_width=True)


if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
if "raw_reviews" not in st.session_state:
    st.session_state.raw_reviews = None
if "game_info" not in st.session_state:
    st.session_state.game_info = None
if "analysis_params" not in st.session_state:
    st.session_state.analysis_params = None


if run_button:
    if not app_id.strip().isdigit():
        st.error("请输入正确的 Steam AppID，例如 1245620。")
    else:
        with st.spinner("正在从 Steam 获取评论并分析，请稍等..."):
            try:
                game_info = fetch_game_details(app_id.strip())
                raw_reviews = fetch_steam_reviews(
                    app_id=app_id.strip(),
                    max_reviews=max_reviews,
                    language=language[0],
                    review_type=review_type[0],
                )
            except Exception as exc:
                st.error(f"Steam 评论获取失败：{exc}")
                st.stop()
            result = analyze_reviews(raw_reviews)
            st.session_state.raw_reviews = raw_reviews
            st.session_state.analysis_result = result
            st.session_state.game_info = game_info
            st.session_state.analysis_params = {
                "app_id": app_id.strip(),
                "language": language[1],
                "review_type": review_type[1],
                "requested_reviews": max_reviews,
            }


result = st.session_state.analysis_result

if result is None:
    st.info("在左侧输入 AppID 后点击“开始分析”。默认 AppID 可用于测试。")
    st.stop()


summary = result["summary"]
reviews_df = result["reviews"]
keyword_df = result["keywords"]
game_info = st.session_state.game_info
analysis_params = st.session_state.analysis_params or {}
report = build_product_report(result, game_info)

if game_info:
    st.markdown(
        f"""
        <div class="game-summary">
          <div class="game-title">当前分析游戏：{game_info['name']}</div>
          <div class="game-meta">
            AppID：{analysis_params.get('app_id', app_id)} ｜ 语言：{analysis_params.get('language', language[1])} ｜ 评论类型：{analysis_params.get('review_type', review_type[1])} ｜ 有效评论：{summary['total_reviews']:,} 条
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


metric_cols = st.columns(5)
metric_cols[0].metric("有效评论", f"{summary['total_reviews']:,}")
metric_cols[1].metric("Steam 好评率", f"{summary['steam_positive_rate']:.1%}")
metric_cols[2].metric("AI 正向率", f"{summary['ai_positive_rate']:.1%}")
metric_cols[3].metric("AI 负向率", f"{summary['ai_negative_rate']:.1%}")
metric_cols[4].metric("平均游玩时长", f"{summary['avg_playtime_hours']:.1f} h")
if summary.get("filtered_invalid_reviews", 0):
    st.caption(f"已自动过滤 {summary['filtered_invalid_reviews']} 条疑似广告、导流或无关评论。")


left_col, right_col = st.columns([1.2, 1])

with left_col:
    st.subheader("情绪分布")
    st.markdown("<div class='section-note'>结合 Steam 推荐字段、SnowNLP 分数和游戏评论语境词典综合判断。</div>", unsafe_allow_html=True)
    sentiment_counts = reviews_df["sentiment_label"].value_counts().reset_index()
    sentiment_counts.columns = ["情绪", "评论数"]
    fig = px.pie(
        sentiment_counts,
        names="情绪",
        values="评论数",
        color="情绪",
        color_discrete_map={"正向": "#2A9D8F", "中性": "#E9C46A", "负向": "#E76F51"},
    )
    st.plotly_chart(fig, use_container_width=True)

with right_col:
    st.subheader("高频关键词")
    st.markdown("<div class='section-note'>用于观察玩家讨论热点、满意点和潜在痛点。</div>", unsafe_allow_html=True)
    st.dataframe(keyword_df, use_container_width=True, hide_index=True)


st.subheader("评论时间趋势")
st.markdown("<div class='section-note'>可按全部、最近 7 天、最近 30 天或自定义日期查看情绪变化。</div>", unsafe_allow_html=True)
trend_source_df = reviews_df.dropna(subset=["created_date"]).copy()

date_cols = st.columns([1, 1.4])
with date_cols[0]:
    date_range_mode = st.selectbox(
        "时间范围",
        options=["全部", "最近 7 天", "最近 30 天", "自定义"],
        index=0,
    )

if not trend_source_df.empty:
    min_date = trend_source_df["created_date"].min()
    max_date = trend_source_df["created_date"].max()

    if date_range_mode == "最近 7 天":
        start_date = max_date - pd.Timedelta(days=6)
        end_date = max_date
    elif date_range_mode == "最近 30 天":
        start_date = max_date - pd.Timedelta(days=29)
        end_date = max_date
    elif date_range_mode == "自定义":
        with date_cols[1]:
            selected_range = st.date_input(
                "选择日期区间",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
            )
        if isinstance(selected_range, tuple) and len(selected_range) == 2:
            start_date, end_date = selected_range
        else:
            start_date, end_date = min_date, max_date
    else:
        start_date, end_date = min_date, max_date

    trend_source_df = trend_source_df[
        (trend_source_df["created_date"] >= start_date)
        & (trend_source_df["created_date"] <= end_date)
    ]

trend_df = (
    trend_source_df
    .groupby(["created_date", "sentiment_label"])
    .size()
    .reset_index(name="评论数")
)
if trend_df.empty:
    st.warning("当前评论数据缺少时间信息，无法绘制趋势图。")
else:
    fig = px.bar(
        trend_df,
        x="created_date",
        y="评论数",
        color="sentiment_label",
        color_discrete_map={"正向": "#2A9D8F", "中性": "#E9C46A", "负向": "#E76F51"},
    )
    fig.update_xaxes(rangeslider_visible=True)
    st.plotly_chart(fig, use_container_width=True)


st.subheader("玩家情绪分析报告")
with st.container(border=True):
    st.markdown(report)


download_cols = st.columns(2)
with download_cols[0]:
    st.download_button(
        "下载清洗后评论 CSV",
        data=reviews_df.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"steam_reviews_{app_id}_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        use_container_width=True,
    )
with download_cols[1]:
    st.download_button(
        "下载分析报告 Markdown",
        data=report.encode("utf-8-sig"),
        file_name=f"steam_report_{app_id}_{datetime.now().strftime('%Y%m%d')}.md",
        mime="text/markdown",
        use_container_width=True,
    )


with st.expander("查看原始分析数据"):
    st.dataframe(reviews_df, use_container_width=True)
