"""跨游戏下载器公用的本地文件校验与原子写入。

只处理安全的磁盘操作。资源地址、身份验证、CDN 回退和解包由游戏适配器负责。
"""
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path


def file_ready(path: str | Path, *, expected_size: int | None = None,
               expected_md5: str | None = None) -> bool:
    """检查文件完整性；只有在调用方给定 MD5 时才额外计算摘要。"""
    candidate = Path(path)
    try:
        if not candidate.is_file():
            return False
        size = candidate.stat().st_size
        if size <= 0 or expected_size is not None and size != expected_size:
            return False
        if expected_md5 is None:
            return True
        digest = hashlib.md5()  # noqa: S324 - 游戏资源官方完整性清单使用 MD5
        with candidate.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower() == expected_md5.lower()
    except OSError:
        return False


def atomic_write_bytes(destination: str | Path, payload: bytes,
                       *, expected_size: int | None = None,
                       expected_md5: str | None = None) -> None:
    """校验后写同目录临时文件并原子替换；失败不破坏已存在资源。"""
    target = Path(destination)
    if not payload or expected_size is not None and len(payload) != expected_size:
        raise ValueError(f"资源数据为空或长度不匹配：{target}")
    if expected_md5 is not None:
        digest = hashlib.md5(payload).hexdigest()  # noqa: S324 - 与源站清单对照
        if digest.lower() != expected_md5.lower():
            raise ValueError(f"资源 MD5 不匹配：{target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary_name = None
    try:
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as output:
            temporary_name = output.name
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary_name, target)
        temporary_name = None
    finally:
        if temporary_name is not None:
            Path(temporary_name).unlink(missing_ok=True)
