"""供应商配置存储（多档案，可选中当前使用的）。"""

from __future__ import annotations

import os

import yaml


class SupplierStore:
    """把多个供应商配置存为 suppliers/<名称>.yaml，并记录当前使用的档案。"""

    _CURRENT_FILE = ".current"

    def __init__(self, root: str = "suppliers") -> None:
        self.root = root
        os.makedirs(self.root, exist_ok=True)
        if not self.list():
            self.save("默认供应商", {"company_type": "企业"})

    def _path(self, name: str) -> str:
        return os.path.join(self.root, name + ".yaml")

    def list(self) -> list[str]:
        names = [os.path.splitext(f)[0] for f in os.listdir(self.root) if f.endswith(".yaml")]
        return sorted(names)

    def load(self, name: str) -> dict:
        try:
            with open(self._path(name), encoding="utf-8") as handle:
                return yaml.safe_load(handle) or {}
        except FileNotFoundError:
            return {}

    def save(self, name: str, data: dict) -> None:
        with open(self._path(name), "w", encoding="utf-8") as handle:
            yaml.safe_dump(data, handle, allow_unicode=True)

    def delete(self, name: str) -> None:
        try:
            os.remove(self._path(name))
        except FileNotFoundError:
            pass

    def current(self) -> str:
        try:
            with open(os.path.join(self.root, self._CURRENT_FILE), encoding="utf-8") as handle:
                name = handle.read().strip()
                if name and os.path.exists(self._path(name)):
                    return name
        except FileNotFoundError:
            pass
        names = self.list()
        return names[0] if names else "默认供应商"

    def set_current(self, name: str) -> None:
        with open(os.path.join(self.root, self._CURRENT_FILE), "w", encoding="utf-8") as handle:
            handle.write(name)
