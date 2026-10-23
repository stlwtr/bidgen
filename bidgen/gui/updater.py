"""版本更新检查：从远程 version.json 拉取最新版本号，对比本地版本。"""

from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass

from .version import VERSION

# version.json 提交到 dev 分支后，可通过该 Gitee raw URL 访问
UPDATE_URL = "https://raw.giteeusercontent.com/yanglishuan/bidgen/raw/dev/version.json"
_TIMEOUT = 8


@dataclass
class UpdateInfo:
    current: str
    latest: str
    download_url: str
    notes: str

    @property
    def has_update(self) -> bool:
        return _version_tuple(self.latest) > _version_tuple(self.current)


def _version_tuple(v: str) -> tuple:
    """语义化版本转可比较元组（如 '1.2.3' -> (1, 2, 3)）。"""
    parts = []
    for p in str(v).split("."):
        try:
            parts.append(int(p))
        except ValueError:
            parts.append(0)
    return tuple(parts)


def fetch_latest(url: str = UPDATE_URL, timeout: int = _TIMEOUT) -> dict:
    """拉取远程 version.json；网络/解析失败返回空 dict。"""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "bidgen-updater"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:  # noqa: BLE001 - 网络失败按无更新处理
        return {}


def check_update(url: str = UPDATE_URL, timeout: int = _TIMEOUT) -> UpdateInfo | None:
    """拉取并返回 UpdateInfo；失败返回 None。"""
    data = fetch_latest(url, timeout)
    if not data or "version" not in data:
        return None
    return UpdateInfo(
        current=VERSION,
        latest=str(data["version"]),
        download_url=str(data.get("download_url", "")),
        notes=str(data.get("notes", "")),
    )
