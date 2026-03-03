"""@File: data_cache.py
@Contains: [DataCache, get_cache]
@Responsibilities:
    - 管理数据缓存的存取和生命周期
    - 实现24小时有效期检查
    - 提供降级策略：无法获取新数据时使用过期缓存
@Non-Responsibilities:
    - 不负责具体的数据获取逻辑
    - 不负责数据格式转换
@Input: 缓存键名、数据内容、有效期配置
@Output: 缓存数据或 None
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Any, Optional, Dict
from pathlib import Path


class DataCache:
    """数据缓存管理器，支持有效期检查和降级策略。"""

    DEFAULT_CACHE_DIR = "data_cache"
    DEFAULT_VALIDITY_HOURS = 24

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        validity_hours: int = DEFAULT_VALIDITY_HOURS
    ):
        """
        初始化缓存管理器。

        Args:
            cache_dir: 缓存目录路径
            validity_hours: 缓存有效时长（小时）
        """
        self.cache_dir = Path(cache_dir or self.DEFAULT_CACHE_DIR)
        self.validity_hours = validity_hours
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """确保缓存目录存在。"""
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def _get_cache_path(self, key: str) -> Path:
        """获取缓存文件路径。"""
        # 使用 hash 避免文件名中的特殊字符问题
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"

    def _get_meta_path(self) -> Path:
        """获取缓存元数据文件路径。"""
        return self.cache_dir / "cache_meta.json"

    def _load_meta(self) -> Dict[str, Dict]:
        """加载缓存元数据。"""
        meta_path = self._get_meta_path()
        if meta_path.exists():
            try:
                with open(meta_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_meta(self, meta: Dict[str, Dict]) -> None:
        """保存缓存元数据。"""
        meta_path = self._get_meta_path()
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(meta, f, ensure_ascii=False, indent=2)

    def get(
        self,
        key: str,
        allow_expired: bool = True
    ) -> Optional[Dict[str, Any]]:
        """
        获取缓存数据。

        Args:
            key: 缓存键名
            allow_expired: 是否允许返回过期缓存（降级策略）

        Returns:
            缓存数据字典，包含 data 和 metadata；如果不存在则返回 None
        """
        cache_path = self._get_cache_path(key)

        if not cache_path.exists():
            return None

        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                cached = json.load(f)

            # 检查有效期
            cached_time = datetime.fromisoformat(cached.get("cached_at", ""))
            is_expired = datetime.now() > cached_time + timedelta(hours=self.validity_hours)

            if is_expired and not allow_expired:
                return None

            # 添加过期标记
            cached["is_expired"] = is_expired
            cached["cache_age_hours"] = (datetime.now() - cached_time).total_seconds() / 3600

            return cached

        except (json.JSONDecodeError, IOError, ValueError) as e:
            print(f"[Cache] Error reading cache for key '{key}': {e}")
            return None

    def set(
        self,
        key: str,
        data: Any,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        设置缓存数据。

        Args:
            key: 缓存键名
            data: 要缓存的数据
            metadata: 额外的元数据

        Returns:
            是否成功保存
        """
        cache_path = self._get_cache_path(key)

        cache_entry = {
            "key": key,
            "data": data,
            "cached_at": datetime.now().isoformat(),
            "validity_hours": self.validity_hours,
            "metadata": metadata or {}
        }

        try:
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(cache_entry, f, ensure_ascii=False, indent=2, default=str)
            return True
        except IOError as e:
            print(f"[Cache] Error writing cache for key '{key}': {e}")
            return False

    def delete(self, key: str) -> bool:
        """删除缓存。"""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            try:
                cache_path.unlink()
                return True
            except IOError:
                return False
        return False

    def clear_expired(self) -> int:
        """
        清理所有过期缓存。

        Returns:
            清理的缓存数量
        """
        cleared = 0
        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name == "cache_meta.json":
                continue
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                cached_time = datetime.fromisoformat(cached.get("cached_at", ""))
                if datetime.now() > cached_time + timedelta(hours=self.validity_hours):
                    cache_file.unlink()
                    cleared += 1
            except (json.JSONDecodeError, IOError, ValueError):
                continue
        return cleared

    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息。"""
        total_files = 0
        total_size = 0
        expired_count = 0

        for cache_file in self.cache_dir.glob("*.json"):
            if cache_file.name == "cache_meta.json":
                continue
            total_files += 1
            total_size += cache_file.stat().st_size

            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cached = json.load(f)
                cached_time = datetime.fromisoformat(cached.get("cached_at", ""))
                if datetime.now() > cached_time + timedelta(hours=self.validity_hours):
                    expired_count += 1
            except (json.JSONDecodeError, IOError, ValueError):
                expired_count += 1

        return {
            "total_files": total_files,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "expired_count": expired_count,
            "valid_count": total_files - expired_count,
            "validity_hours": self.validity_hours
        }


# 全局缓存实例
_cache_instance: Optional[DataCache] = None


def get_cache(cache_dir: Optional[str] = None, validity_hours: int = 24) -> DataCache:
    """
    获取全局缓存实例。

    Args:
        cache_dir: 缓存目录（仅首次调用有效）
        validity_hours: 有效时长（仅首次调用有效）

    Returns:
        DataCache 实例
    """
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = DataCache(cache_dir, validity_hours)
    return _cache_instance


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """
    生成缓存键名。

    Args:
        prefix: 键名前缀（如 'stock', 'fundamentals'）
        *args: 位置参数
        **kwargs: 关键字参数

    Returns:
        格式化的缓存键名
    """
    parts = [prefix]
    for arg in args:
        if arg is not None:
            parts.append(str(arg))
    for k, v in sorted(kwargs.items()):
        if v is not None:
            parts.append(f"{k}_{v}")
    return "_".join(parts)