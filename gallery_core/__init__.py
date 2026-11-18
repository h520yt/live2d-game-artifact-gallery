"""游戏展示柜跨游戏资源管理核心（第一阶段）。"""
from .catalog import GAME_MANIFESTS, SCHEMA_VERSION, build_catalog, verify_catalog

__all__ = ["GAME_MANIFESTS", "SCHEMA_VERSION", "build_catalog", "verify_catalog"]
