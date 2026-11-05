#!/usr/bin/env python3
"""Đóng gói NomNom UI resource pack (Paper 1.21.11) + merge weapons_rp.

Nguyên tắc:
- Asset UI thật lấy từ work/rp_src/assets/**. Phần nào chưa có thì lấy placeholder
  từ work/rp_build/placeholders/ (sinh bởi make_placeholders.py) và ghi rõ vào
  PLACEHOLDERS.txt + build_report.json.
- weapons_rp.zip: copy nguyên byte các entry assets/weapons/** (giữ đường dẫn),
  không copy pack.mcmeta/pack.png của pack nguồn.
- pack.mcmeta dùng pack_format của RESOURCE PACK cho 1.21.11 = 75
  (xác minh: unzip -p local_server/cache/mojang_1.21.11.jar version.json
   -> pack_version.resource_major = 75; 94 là data_major).
- Zip deterministic: thứ tự sort, timestamp cố định, không chứa file rác.

Chạy:
  python work/rp_build/build_pack.py
  python work/rp_build/build_pack.py --version 1.0.0 --out work/rp_build/dist/NomNomUI-v1.0.0.zip
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent
PROJECT = BUILD_DIR.parents[1]
UI_SRC = PROJECT / "work" / "rp_src"
if not UI_SRC.is_dir() and (BUILD_DIR.parent / "assets").is_dir():
    UI_SRC = BUILD_DIR.parent  # repo layout: resourcepack/assets
PLACEHOLDER_DIR = BUILD_DIR / "placeholders"
STAGE_DIR = BUILD_DIR / "stage"
DEFAULT_WEAPONS = PROJECT / "downloads" / "weapons_rp.zip"
OFL_SRC = PROJECT / "work" / "nn4_font_probe" / "OFL.txt"

# 1.21.11 resource pack format (KHÔNG phải 94 — 94 là data pack format).
PACK_FORMAT = 75
ZIP_DATE = (2026, 1, 1, 0, 0, 0)

WEAPONS_PROJECT = {
    "title": "weapons-plus",
    "author": "jfrost3712",
    "modrinth_id": "4pmYLtZ9",
    "slug": "weapon-plus",
    "url": "https://modrinth.com/project/4pmYLtZ9",
    "license": "CC-BY-4.0",
    "license_url": "https://creativecommons.org/licenses/by/4.0/",
}

README_PACK = """# NomNom UI — resource pack

Pack UI chính thức của **NomNom SMP** (Paper 1.21.11): font tiếng Việt, bộ icon glyph
và texture GUI cho market / cash / land / casino / mini.

- Phiên bản: **{version}**
- `pack_format`: **{pack_format}** (resource pack, Minecraft 1.21.11)
- Build: `resourcepack/build/build_pack.py` — zip deterministic, sinh sha1/sha256.
- Cài đặt: chép zip vào `resourcepacks/`, hoặc gửi qua Paper `Player#addResourcePack`.
- Sau khi đổi pack, client cần **F3+T** hoặc reconnect để nạp lại font.

## Nội dung
- `assets/minecraft/font/default.json` — override font mặc định (khi có atlas thật)
- `assets/nomnom/font/ui.json` — font icon `nomnom:ui` (PUA U+E000–U+E02F)
- `assets/nomnom/textures/font/*` — atlas font/icon
- `assets/nomnom/textures/gui/*`, `textures/item/ui/*` — texture kit
- `assets/nomnom/models/item/ui/*`, `items/ui/*` — item model / item definition
- `assets/weapons/**` — texture vũ khí weapons-plus (CC-BY-4.0)

## Ghi công (bắt buộc)
- **weapons-plus** — tác giả **jfrost3712**, Modrinth project
  [`4pmYLtZ9`]({weapons_url}), giấy phép **CC-BY-4.0**.
  Xem `ATTRIBUTION.md` để biết phạm vi và yêu cầu ghi công.
- **Be Vietnam Pro** — SIL Open Font License 1.1, xem `LICENSE-OFL.txt`.
- Phần UI tự thiết kế: © NomNom SMP.

## Trạng thái build
{status}
"""

ATTR_MD = """# Ghi công & giấy phép — NomNom UI resource pack

Pack này phân phối lại tài sản của bên thứ ba. Khi dùng/chia sẻ lại, giữ nguyên
file này và các ghi công dưới đây.

## 1. weapons-plus (texture vũ khí)

| Trường | Giá trị |
|---|---|
| Tên dự án | **weapons-plus** (slug `weapon-plus`) |
| Tác giả | **jfrost3712** |
| Modrinth project ID | `4pmYLtZ9` |
| Trang dự án | https://modrinth.com/project/4pmYLtZ9 |
| Giấy phép | **Creative Commons Attribution 4.0 International (CC-BY-4.0)** |
| Văn bản giấy phép | https://creativecommons.org/licenses/by/4.0/ |
| Phạm vi trong pack | Toàn bộ `assets/weapons/**` (items, models, textures) |

Yêu cầu của CC-BY-4.0: ghi tên tác giả, link tới giấy phép, link tới nguồn và
**nêu rõ nếu có sửa đổi**. Pack này:

- giữ nguyên đường dẫn `assets/weapons/**` và copy **nguyên byte** từ
  `weapons_rp.zip` nhận được (bản patch tương thích 1.21.11 của dự án gốc);
- **không** sửa thêm texture/model vũ khí trong quá trình đóng gói;
- mọi khác biệt so với bản upstream (nếu có) thuộc về `weapons_rp.zip` nguồn,
  không phải chỉnh sửa của NomNom SMP.

## 2. Font Be Vietnam Pro

| Trường | Giá trị |
|---|---|
| Tên font | **Be Vietnam Pro** (Regular 400 + Bold 700) |
| Tác giả | The Be Vietnam Pro Project Authors, Copyright 2021 |
| Giấy phép | **SIL Open Font License 1.1 (OFL-1.1)** |
| Nguồn | Google Fonts — `ofl/bevietnampro` |
| Văn bản giấy phép | `LICENSE-OFL.txt` (kèm trong pack) |

OFL cho phép nhúng/phân phối font trong resource pack, kể cả bản raster hóa;
không được bán font riêng lẻ. Tên font gốc được giữ trong ghi công này.

## 3. Phần tự thiết kế

Palette, panel 9-slice, button, badge tier, bố cục menu, icon glyph và toàn bộ
script đóng gói: **© NomNom SMP 2026**. Được phát hành kèm server NomNom SMP.

## 4. Ghi công trong sản phẩm

- README của repo và của pack đều có mục "Ghi công (bắt buộc — CC-BY-4.0)".
- Trang phát hành GitHub Releases phải giữ nguyên phần ghi công này.
"""


def sha1_file(path: Path) -> str:
    h = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for p in src.rglob("*"):
        if p.is_file():
            rel = p.relative_to(src)
            out = dst / rel
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, out)
            n += 1
    return n


def reset_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def font_refs_to_asset(ref: str) -> Path:
    """'nomnom:font/icons.png' -> assets/nomnom/textures/font/icons.png"""
    ns, _, path = ref.partition(":")
    return Path("assets") / ns / "textures" / path


def check_font_json(stage: Path, rel_json: str) -> tuple[bool, list[str]]:
    """Trả (hợp lệ, danh sách bitmap thiếu)."""
    p = stage / rel_json
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        return False, [f"JSON lỗi: {e}"]
    missing = []
    for prov in data.get("providers", []):
        if prov.get("type") == "bitmap" and "file" in prov:
            asset = font_refs_to_asset(prov["file"])
            if not (stage / asset).is_file():
                missing.append(asset.as_posix())
    return (not missing), missing


def merge_ui(stage: Path, placeholder_files: list[str], use_placeholders: bool,
             report: dict, ui_src: Path) -> None:
    if (ui_src / "assets").is_dir():
        n = copy_tree(ui_src / "assets", stage / "assets")
        report["ui_source_present"] = True
        report["ui_files_from_source"] = n
    else:
        report["ui_source_present"] = False
        report["ui_files_from_source"] = 0

    # pack.png thật (nếu agent texture có) — chưa có thì placeholder
    if (ui_src / "pack.png").is_file():
        shutil.copyfile(ui_src / "pack.png", stage / "pack.png")
        report["pack_png"] = "source"
    # LICENSE* từ nguồn
    for lic in ui_src.glob("LICENSE*"):
        if lic.is_file():
            shutil.copyfile(lic, stage / lic.name)

    if use_placeholders:
        for rel in placeholder_files:
            dst = stage / rel
            if not dst.exists():
                src = PLACEHOLDER_DIR / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
                report["placeholders_used"].append(rel)
        if "pack.png" in report["placeholders_used"]:
            report["placeholders_used"].remove("pack.png")
            report["pack_png"] = "generated"
        elif (stage / "pack.png").is_file() and report["pack_png"] is None:
            report["pack_png"] = "source"

    # Font JSON an toàn: nếu thiếu bitmap được tham chiếu thì bỏ override để
    # không làm hỏng toàn bộ text của client.
    for rel_json in sorted((stage / "assets").glob("*/font/*.json")):
        rel = rel_json.relative_to(stage).as_posix()
        ok, missing = check_font_json(stage, rel)
        if ok:
            continue
        if rel == "assets/minecraft/font/default.json":
            rel_json.unlink()
            report["skipped_font_json"].append({"file": rel, "missing": missing,
                                                "reason": "override minecraft:default thiếu atlas — bỏ để giữ font vanilla"})
        else:
            # ui.json thiếu atlas: thay bằng bộ placeholder (ui.json + icons.png)
            if use_placeholders:
                for fix in ("assets/nomnom/font/ui.json",
                            "assets/nomnom/textures/font/icons.png"):
                    if (PLACEHOLDER_DIR / fix).is_file():
                        dst = stage / fix
                        dst.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(PLACEHOLDER_DIR / fix, dst)
                        report["placeholders_used"].append(fix)
                report["skipped_font_json"].append({"file": rel, "missing": missing,
                                                    "reason": "thay bằng placeholder ui.json + icons.png"})
            else:
                rel_json.unlink()
                report["skipped_font_json"].append({"file": rel, "missing": missing,
                                                    "reason": "bỏ vì thiếu atlas"})


def merge_weapons(stage: Path, weapons_zip: Path, report: dict) -> None:
    if not weapons_zip.is_file():
        raise FileNotFoundError(f"không thấy weapons zip: {weapons_zip}")
    count = 0
    skipped = []
    with zipfile.ZipFile(weapons_zip) as z:
        for info in z.infolist():
            name = info.filename
            if info.is_dir():
                continue
            if not name.startswith("assets/weapons/"):
                skipped.append(name)
                continue
            dst = stage / name
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(z.read(name))
            count += 1
    report["weapons_files"] = count
    report["weapons_root_files_skipped"] = skipped


def normalize_item_definitions(stage: Path, report: dict) -> None:
    """Sửa item definition trỏ sai namespace model (agent texture ghi `nomnom:ui/x`
    trong khi model nằm ở `nomnom:item/ui/x`). Chỉ sửa khi model đích tồn tại;
    ghi lại từng thay đổi vào build_report.json."""
    for p in sorted((stage / "assets").glob("*/items/**/*.json")):
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        model = (data.get("model") or {}).get("model")
        if not model or ":" not in model:
            continue
        ns, _, path = model.partition(":")
        if (stage / f"assets/{ns}/models/{path}.json").is_file():
            continue
        alt = f"item/{path}"
        if not (stage / f"assets/{ns}/models/{alt}.json").is_file():
            continue
        data["model"]["model"] = f"{ns}:{alt}"
        p.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                     encoding="utf-8")
        report["normalized_item_definitions"].append({
            "file": p.relative_to(stage).as_posix(),
            "from": model, "to": f"{ns}:{alt}",
        })


def write_meta_files(stage: Path, version: str, report: dict, ui_src: Path) -> None:
    desc = f"§6NomNom UI §8• §7Font tiếng Việt, icon & GUI §8• §7v{version}"
    mcmeta = {"pack": {"pack_format": PACK_FORMAT, "description": desc}}
    (stage / "pack.mcmeta").write_text(
        json.dumps(mcmeta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if report["placeholders_used"]:
        status = (f"**Build có {len(report['placeholders_used'])} file placeholder** — "
                  "các asset thật chưa được giao. Xem `PLACEHOLDERS.txt`.\n"
                  "Không dùng bản này để đánh giá thẩm mỹ/visual cuối.")
    else:
        status = "Đầy đủ asset thật từ `work/rp_src/` (không có placeholder)."

    (stage / "README.md").write_text(README_PACK.format(
        version=version, pack_format=PACK_FORMAT,
        weapons_url=WEAPONS_PROJECT["url"], status=status), encoding="utf-8")
    (stage / "ATTRIBUTION.md").write_text(ATTR_MD, encoding="utf-8")
    ofl = ui_src / "LICENSE-OFL.txt"
    shutil.copyfile(ofl if ofl.is_file() else OFL_SRC,
                    stage / "LICENSE-OFL.txt")
    # sửa link tương đối trong FONT-INFO (nguồn ghi 4 cấp ../, thực tế 3 cấp từ pack root)
    info = stage / "assets/nomnom/font/FONT-INFO.txt"
    if info.is_file():
        txt = info.read_text(encoding="utf-8")
        fixed = txt.replace("../../../../LICENSE-OFL.txt", "../../../LICENSE-OFL.txt")
        if fixed != txt:
            info.write_text(fixed, encoding="utf-8")
            report["doc_fixes"].append({"file": "assets/nomnom/font/FONT-INFO.txt",
                                        "change": "sửa đường dẫn OFL tương đối"})

    if report["placeholders_used"]:
        lines = [
            "DANH SÁCH PLACEHOLDER — NomNom UI resource pack",
            "=" * 52,
            "",
            "Các file dưới đây do work/rp_build/make_placeholders.py sinh ra vì",
            "asset thật từ agent FONT & ICON / TEXTURE KIT chưa có tại thời điểm build.",
            "Chúng được thiết kế để pack HỢP LỆ (không lỗi texture/font), KHÔNG phải",
            "asset cuối. Khi có file thật trong work/rp_src/, build lại sẽ tự thay thế.",
            "",
        ]
        for rel in sorted(report["placeholders_used"]):
            lines.append(f"- {rel}")
        lines += ["", f"Tổng: {len(report['placeholders_used'])} file placeholder.",
                  f"Build lúc: {report['build_time']} UTC", ""]
        (stage / "PLACEHOLDERS.txt").write_text("\n".join(lines), encoding="utf-8")


def validate_stage(stage: Path) -> tuple[int, int]:
    """Parse toàn bộ JSON + đếm file. Raise nếu JSON hỏng."""
    total = 0
    for p in stage.rglob("*"):
        if p.is_file():
            total += 1
            if p.suffix.lower() == ".json":
                try:
                    json.loads(p.read_text(encoding="utf-8"))
                except json.JSONDecodeError as e:
                    raise ValueError(f"JSON hỏng: {p.relative_to(stage)}: {e}") from e
    return total, sum(1 for p in stage.rglob("*.json") if p.is_file())


def zip_stage(stage: Path, out_zip: Path) -> int:
    out_zip.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in stage.rglob("*") if p.is_file())
    with zipfile.ZipFile(out_zip, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9) as z:
        for p in files:
            rel = p.relative_to(stage).as_posix()
            info = zipfile.ZipInfo(rel, date_time=ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                       compresslevel=9)
    return len(files)


def main() -> int:
    ap = argparse.ArgumentParser(description="Đóng gói NomNom UI resource pack")
    ap.add_argument("--version", default="1.1.0")
    ap.add_argument("--out", default=str(BUILD_DIR / "dist" / "NomNomUI-v1.1.0.zip"))
    ap.add_argument("--weapons", default=str(DEFAULT_WEAPONS))
    ap.add_argument("--ui-src", default=str(UI_SRC),
                    help="thư mục nguồn UI (mặc định work/rp_src)")
    ap.add_argument("--no-weapons", action="store_true",
                    help="không merge weapons (dùng khi --ui-src đã chứa assets/weapons)")
    ap.add_argument("--no-placeholders", action="store_true",
                    help="fail nếu thiếu asset thay vì dùng placeholder")
    args = ap.parse_args()

    # Tái sinh placeholder để đảm bảo idempotent
    import make_placeholders  # noqa: E402  (script cùng thư mục)
    import importlib
    importlib.reload(make_placeholders)
    reset_dir(PLACEHOLDER_DIR)
    placeholder_files = make_placeholders.build(PLACEHOLDER_DIR)

    reset_dir(STAGE_DIR)
    report: dict = {
        "version": args.version,
        "pack_format": PACK_FORMAT,
        "build_time": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ui_source_present": False,
        "ui_files_from_source": 0,
        "placeholders_used": [],
        "skipped_font_json": [],
        "normalized_item_definitions": [],
        "doc_fixes": [],
        "weapons_files": 0,
        "weapons_root_files_skipped": [],
        "pack_png": None,
    }

    ui_src = Path(args.ui_src)
    merge_ui(STAGE_DIR, placeholder_files, not args.no_placeholders, report, ui_src)
    if args.no_placeholders and not report["ui_source_present"]:
        raise SystemExit("thiếu asset thật và --no-placeholders được bật: "
                         + ", ".join(report["placeholders_used"][:5]))

    normalize_item_definitions(STAGE_DIR, report)
    if args.no_weapons:
        report["weapons_files"] = sum(
            1 for p in (STAGE_DIR / "assets" / "weapons").rglob("*") if p.is_file())
        report["weapons_merged"] = False
    else:
        merge_weapons(STAGE_DIR, Path(args.weapons), report)
        report["weapons_merged"] = True
    write_meta_files(STAGE_DIR, args.version, report, ui_src)

    total, json_count = validate_stage(STAGE_DIR)
    out_zip = Path(args.out)
    zip_count = zip_stage(STAGE_DIR, out_zip)

    report.update({
        "output": str(out_zip),
        "files": zip_count,
        "json_files": json_count,
        "bytes": out_zip.stat().st_size,
        "sha1": sha1_file(out_zip),
        "sha256": sha256_file(out_zip),
        "complete": not report["placeholders_used"],
        "placeholder_count": len(report["placeholders_used"]),
    })
    report_path = BUILD_DIR / "build_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")

    print("=" * 64)
    print(f"NomNomUI v{args.version}")
    print(f"  output      : {out_zip}")
    print(f"  files       : {zip_count} (json: {json_count}, weapons: {report['weapons_files']})")
    print(f"  bytes       : {report['bytes']}")
    print(f"  pack_format : {PACK_FORMAT} (resource pack 1.21.11)")
    print(f"  UI source   : {'có' if report['ui_source_present'] else 'KHÔNG — placeholder'}"
          f" ({report['ui_files_from_source']} file)")
    print(f"  placeholder : {report['placeholder_count']} file")
    print(f"  item def fix: {len(report['normalized_item_definitions'])} file")
    for item in report["skipped_font_json"]:
        print(f"  ! font json : {item['file']} — {item['reason']} (thiếu {item['missing']})")
    print(f"  sha1        : {report['sha1']}")
    print(f"  sha256      : {report['sha256']}")
    print(f"  report      : {report_path}")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    sys.exit(main())
