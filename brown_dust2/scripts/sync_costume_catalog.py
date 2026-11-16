#!/usr/bin/env python3
"""同步 BD2 可核对的服装目录；只同步角色元数据，不下载游戏素材。"""
import argparse
import json
import re
from datetime import date
from pathlib import Path
from urllib.request import Request, urlopen

BASE = Path(__file__).resolve().parents[1]
PRESTIGE = BASE / "curated_prestige.json"
CATALOG = BASE / "costume_catalog.json"
SOURCE_URL = (
    "https://raw.githubusercontent.com/Jelosus2/BD2-L2D-Viewer/"
    "main/src/utils/character_list.ts"
)
ENTRY = re.compile(r'"([0-9]{6})"\s*:\s*\{\s*(.*?)\n\s*\},', re.S)
FIELD = re.compile(r'"([A-Za-z_][A-Za-z_0-9]*)"\s*:\s*"([^"]*)"')

SPECIAL_SKINS = {
    ("Helena", "Rising Star"), ("Darian", "Herald of Enlightenment"),
    ("Michaela", "True Liberation"), ("Nebris", "Lucky Bikini"),
    ("Sylvia", "Crimson Lotus"), ("Dalvi", "Butterfly Dream"),
    ("Blade", "Tender Dream"), ("Tenka Izumo", "Special Date"),
}
FATED_GUESTS = {
    ("Nebris", "New Hire"), ("Morpeah", "Daydream Bunny"),
    ("Loen", "Celebrity Bunny"), ("Teresse", "Medical Club"),
    ("Elise", "Code Name O"), ("Wilhelmina", "Water Park Queen"),
    ("Sylvia", "Bikini Agent"), ("Angelica", "Neon Savior"),
    ("Eclipse", "Nightmare Bunny"), ("Tyr", "Innocent Bunny"),
    ("Ventana", "Onsen Practitioner"), ("Olivier", "Retired Legend"),
    ("Palette", "Miracle Violet"), ("Granhildr", "Combat Medic"),
    ("Dalvi", "Bright Moon"),
}


def costume_tier(character, costume):
    """按 BD2DB 独立皮肤/访客分类标记；其他套装不擅自评级。"""
    key = (character, costume)
    if key in SPECIAL_SKINS:
        return "Special Skin"
    if key in FATED_GUESTS:
        return "Fated Guest"
    return "Costume"




def parse_index(source_text, prestige_skins):
    """上游目录映射只有来源确认，不等于对应骨骼素材已真实下载。"""
    reserved = {
        entry["roles"]["character"].split("/")[-1]
        for entry in prestige_skins
        if "character" in entry.get("roles", {})
    }
    result = []
    seen = set()
    for match in ENTRY.finditer(source_text):
        costume_id = match.group(1)
        fields = dict(FIELD.findall(match.group(2)))
        name = fields.get("charName", "").strip()
        title = fields.get("costumeName", "").strip()
        spine = fields.get("spine", "")
        if not name or not title or title == "???":
            continue
        if "(Npc)" in name or not re.fullmatch(r"char[0-9]{6}", spine):
            continue
        if spine in reserved or costume_id in seen:
            continue
        roles = {"character": "spine/char/" + spine}
        cutscene = fields.get("cutscene", "")
        dating = fields.get("dating", "")
        if re.fullmatch(r"cutscene_char[0-9]{6}", cutscene):
            roles["cutscene"] = "spine/cutscenes/" + cutscene
        if re.fullmatch(r"illust_dating[0-9]+", dating):
            roles["interaction"] = "spine/illust/illust_dating/" + dating
        result.append({
            "id": "costume-" + costume_id,
            "costume_id": costume_id,
            "character": name,
            "character_en": name,
            "skin": title,
            "skin_en": title,
            "tier": costume_tier(name, title),
            "roles": roles,
            "mapping": "upstream_index",
        })
        seen.add(costume_id)
    result.sort(key=lambda entry: (
        -int("interaction" in entry["roles"]),
        -int("cutscene" in entry["roles"]),
        entry["character_en"].lower(),
        entry["costume_id"],
    ))
    return result


def build_catalog(source_text, prestige_skins, generated_on=None):
    skins = parse_index(source_text, prestige_skins)
    return {
        "source": {
            "repository": "Jelosus2/BD2-L2D-Viewer",
            "path": "src/utils/character_list.ts",
            "assets": "myssal/Brown-Dust-2-Asset",
            "notice": "映射来自第三方模型索引；安装时才校验远端资源是否存在",
        },
        "generated_on": generated_on or date.today().isoformat(),
        "skins": skins,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="更新棕色尘埃2非尊爵服装目录")
    parser.add_argument("--source-file", type=Path, help="从本地上游索引文件更新（离线）")
    parser.add_argument("--check", action="store_true", help="只计算条目数，不写文件")
    args = parser.parse_args(argv)
    if args.source_file:
        source = args.source_file.read_text(encoding="utf-8")
    else:
        request = Request(SOURCE_URL, headers={"User-Agent": "BD2-Gallery-Catalog/1.0"})
        with urlopen(request, timeout=45) as response:
            source = response.read().decode("utf-8")
    prestige = json.loads(PRESTIGE.read_text(encoding="utf-8"))["skins"]
    result = build_catalog(source, prestige)
    print("尊爵:", len(prestige), "其它服装:", len(result["skins"]),
          "互动映射:", sum("interaction" in x["roles"] for x in result["skins"]))
    if not args.check:
        if not result["skins"]:
            raise RuntimeError("上游索引解析结果为空，拒绝覆盖现有目录")
        CATALOG.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
        print("已更新:", CATALOG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
