import requests
from typing import Optional


BASE_URL = "https://api.chksz.top/api"


def search_songs(keyword: str, limit: int = 100, offset: int = 0) -> dict:
    resp = requests.get(
        f"{BASE_URL}/163_search",
        params={
            "keyword": keyword,
            "limit": limit,
            "offset": offset,
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_playlist(playlist_id: str) -> dict:
    resp = requests.get(
        f"{BASE_URL}/163_playlist", params={"id": playlist_id}, timeout=15
    )
    resp.raise_for_status()
    return resp.json()


def get_music_info(song_id: str, level: str = "jymaster") -> dict:
    resp = requests.get(
        f"{BASE_URL}/163_music",
        params={
            "id": song_id,
            "level": level,
            "type": "json",
        },
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()


def get_lyric(song_id: str) -> dict:
    resp = requests.get(f"{BASE_URL}/163_lyric", params={"id": song_id}, timeout=15)
    resp.raise_for_status()
    return resp.json()


def download_cover(url: str) -> Optional[bytes]:
    try:
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        return resp.content
    except Exception:
        return None
