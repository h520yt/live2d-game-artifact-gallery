#!/usr/bin/env python3
"""《重返未来：1999》皮肤原画：从维基原始 Portrait 文件下载，无需 GitHub API。

原画和游戏内专属背景是两种资源；禁止用 headskinicon 或模型图集冒充。
图片版权归原权利方，文件仅保存在本地被 Git 忽略的 data/ 目录。
"""
import hashlib
import os
import re
import tempfile
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

CDN = "https://huiji-public.huijistatic.com/res1999/uploads"
MAX_BYTES = 24 * 1024 * 1024


def urls(skin_id):
    sid = str(skin_id)
    if not re.fullmatch(r"\d{6}", sid):
        raise ValueError("原画皮肤 ID 必须为 6 位数字")
    filename = f"Portrait-{sid}.webp"
    # MediaWiki 上传路径：MD5(文件名) 的前1、前2位目录
    digest = hashlib.md5(filename.encode("utf-8")).hexdigest()
    return (
        f"{CDN}/{digest[0]}/{digest[:2]}/{filename}",
        f"https://res1999.huijiwiki.com/wiki/Special:Redirect/file/{filename}",
    )


def dimensions(blob):
    """识别 WebP VP8X/VP8/VP8L 画布尺寸，排除 HTML、头像、截断包。"""
    if (len(blob) < 8192 or len(blob) > MAX_BYTES or blob[:4] != b"RIFF"
            or blob[8:12] != b"WEBP"
            or int.from_bytes(blob[4:8], "little") + 8 != len(blob)):
        return None
    if len(blob) < 30:
        return None
    chunk, size = blob[12:16], int.from_bytes(blob[16:20], "little")
    if size <= 0 or 20 + size > len(blob):
        return None
    data = blob[20:20 + size]
    if chunk == b"VP8X" and len(data) >= 10:
        width = int.from_bytes(data[4:7], "little") + 1
        height = int.from_bytes(data[7:10], "little") + 1
    elif chunk == b"VP8L" and len(data) >= 5 and data[0] == 0x2f:
        width = 1 + data[1] + ((data[2] & 0x3f) << 8)
        height = 1 + (data[2] >> 6) + (data[3] << 2) + ((data[4] & 0x0f) << 10)
    elif chunk == b"VP8 " and len(data) >= 10 and data[3:6] == b"\x9d\x01\x2a":
        width = int.from_bytes(data[6:8], "little") & 0x3fff
        height = int.from_bytes(data[8:10], "little") & 0x3fff
    else:
        return None
    return (width, height) if 320 <= width <= 12000 and 720 <= height <= 12000 else None


def exists(path):
    path = Path(path)
    try:
        if path.is_file() and path.stat().st_size <= MAX_BYTES:
            return dimensions(path.read_bytes()) is not None
    except OSError:
        pass
    return False


def download(skin_id, target, sources=None):
    """验证后原子写入 WebP。下载失败时保留原模型及旧原画，不伪造完成状态。"""
    target = Path(target)
    if exists(target):
        return False
    target.parent.mkdir(parents=True, exist_ok=True)
    failures = []
    for url in (urls(skin_id) if sources is None else sources):
        try:
            # Merui 角色原画和灰机维基是不同图源：Referer 不能固定成灰机，
            # 否则原图服务器可能拒绝外站热链请求。
            host = urllib.parse.urlparse(url).hostname
            headers = {"User-Agent": "Mozilla/5.0 (compatible; personal-art-gallery/1.0)"}
            if host in ("res1999.huijiwiki.com", "huiji-public.huijistatic.com"):
                headers["Referer"] = "https://res1999.huijiwiki.com/"
            elif host == "assets.merui.net":
                headers["Referer"] = "https://uttu.merui.net/"
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=50) as response:
                image = response.read(MAX_BYTES + 1)
            size = dimensions(image)
            if not size:
                raise ValueError("该地址未返回完整的高分辨率 WebP 立绘")
            fd, temporary = tempfile.mkstemp(prefix=".artwork-", suffix=".webp", dir=target.parent)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(image)
                os.replace(temporary, target)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
            print(f"[{skin_id}] 原画 {size[0]}×{size[1]} 已保存到 {target}")
            return True
        except (OSError, ValueError, urllib.error.URLError) as exc:
            failures.append(f"{url}：{exc}")
    raise RuntimeError(f"皮肤 {skin_id} 原画来源不可用，原模型不受影响：" + "；".join(failures))
