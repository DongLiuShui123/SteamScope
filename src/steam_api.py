import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


STEAM_REVIEW_URL = "https://store.steampowered.com/appreviews/{app_id}"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


def fetch_game_details(app_id: str) -> dict[str, Any] | None:
    """Fetch basic Steam store details for a game."""
    session = _build_session()
    response = session.get(
        STEAM_APPDETAILS_URL,
        params={"appids": app_id, "cc": "cn", "l": "schinese"},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    app_payload = payload.get(str(app_id), {})

    if not app_payload.get("success"):
        return None

    data = app_payload.get("data", {})
    name = data.get("name")
    if not name:
        return None

    return {"name": name}


def fetch_steam_reviews(
    app_id: str,
    max_reviews: int = 500,
    language: str = "schinese",
    review_type: str = "all",
) -> list[dict[str, Any]]:
    """Fetch public reviews from the Steam Review API."""
    reviews: list[dict[str, Any]] = []
    cursor = "*"
    session = _build_session()

    while len(reviews) < max_reviews:
        batch_size = min(100, max_reviews - len(reviews))
        params = {
            "json": 1,
            "filter": "recent",
            "language": language,
            "review_type": review_type,
            "purchase_type": "all",
            "num_per_page": batch_size,
            "cursor": cursor,
        }

        response = session.get(
            STEAM_REVIEW_URL.format(app_id=app_id),
            params=params,
            timeout=40,
        )
        response.raise_for_status()
        payload = response.json()

        if payload.get("success") != 1:
            raise RuntimeError("Steam API 返回失败，请检查 AppID 或稍后重试。")

        page_reviews = payload.get("reviews", [])
        if not page_reviews:
            break

        reviews.extend(page_reviews)
        next_cursor = payload.get("cursor")
        if not next_cursor or next_cursor == cursor:
            break

        cursor = next_cursor
        time.sleep(0.4)

    if not reviews:
        raise RuntimeError("没有获取到评论。可以尝试切换语言为“全部”或减少筛选条件。")

    return reviews[:max_reviews]


def _build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=2,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("https://", adapter)
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/126.0 Safari/537.36"
            )
        }
    )
    return session
