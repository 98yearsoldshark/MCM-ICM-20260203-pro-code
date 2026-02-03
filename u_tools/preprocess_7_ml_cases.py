#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预处理工具：把“7-机器学习实战案例及代码”里的难读格式转成可读文本。

目前支持：
- .ipynb -> .py（含 # %% 分块，保留 Markdown 为注释）+ .md（Markdown+代码块）
- .pptx  -> .md（按 slide 提取文字；并按 slide 提取引用图片到本地目录）
- .pdf   -> .txt（调用系统 pdftotext；若缺失则跳过）

输出默认写入：mcm_temp/preprocessed/7-机器学习实战案例及代码/
并尽量保持与源目录一致的相对路径结构，方便对照。
"""

from __future__ import annotations

import argparse
import os
import posixpath
import re
import shutil
import subprocess
import sys
import textwrap
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple


def _localname(tag: str) -> str:
    """提取 XML tag 的 localname（去掉命名空间前缀）。"""
    if "}" in tag:
        return tag.split("}", 1)[1]
    return tag


def _safe_mkdir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def _rel_to(root: Path, p: Path) -> str:
    return os.path.relpath(p, root)


def _read_zip_text(zf: zipfile.ZipFile, member: str) -> str:
    return zf.read(member).decode("utf-8", errors="replace")


def _extract_pptx_slide_text(slide_xml: str) -> List[str]:
    """
    从单个 slide 的 XML 中提取段落文本。

    只做“可读化”而非精确排版：按 a:p 段落收集 a:t。
    """
    # 用标准库 xml.etree 即可；但为了减少命名空间处理的复杂度，这里直接解析 XML。
    import xml.etree.ElementTree as ET

    try:
        root = ET.fromstring(slide_xml)
    except ET.ParseError:
        # 如果 XML 异常，退化为正则粗提取
        texts = re.findall(r"<a:t[^>]*>(.*?)</a:t>", slide_xml, flags=re.IGNORECASE | re.DOTALL)
        return [re.sub(r"\s+", " ", t).strip() for t in texts if t and t.strip()]

    paras: List[str] = []
    for p in root.iter():
        if _localname(p.tag) != "p":
            continue
        runs: List[str] = []
        for t in p.iter():
            if _localname(t.tag) == "t" and t.text:
                runs.append(t.text)
        if runs:
            s = "".join(runs).strip()
            if s:
                paras.append(s)
    # 去重（保持顺序），避免某些模板带来的重复段落
    seen = set()
    out: List[str] = []
    for s in paras:
        if s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out


def _pptx_slide_image_targets(zf: zipfile.ZipFile, slide_index: int) -> List[str]:
    """
    返回 slide{i}.xml 对应的图片 Target（zip 内部路径，形如 ppt/media/image1.png）。
    """
    rels_member = f"ppt/slides/_rels/slide{slide_index}.xml.rels"
    if rels_member not in zf.namelist():
        return []

    import xml.etree.ElementTree as ET

    xml = _read_zip_text(zf, rels_member)
    try:
        root = ET.fromstring(xml)
    except ET.ParseError:
        return []

    # Relationships 默认命名空间
    image_targets: List[str] = []
    for rel in root.iter():
        if _localname(rel.tag) != "Relationship":
            continue
        rel_type = rel.attrib.get("Type", "")
        if not rel_type.endswith("/image"):
            continue
        target = rel.attrib.get("Target", "")
        if not target:
            continue
        # target 是相对 ppt/slides/ 的路径，常见为 ../media/image1.png
        target = target.replace("\\", "/")
        abs_path = posixpath.normpath(posixpath.join("ppt/slides", target))
        if abs_path.startswith("../"):
            # 理论上不会出现，但兜底
            abs_path = abs_path.lstrip("../")
        if abs_path not in zf.namelist():
            continue
        image_targets.append(abs_path)

    # 去重并保持顺序
    seen = set()
    out: List[str] = []
    for t in image_targets:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def preprocess_pptx(in_path: Path, out_md_path: Path) -> None:
    """
    将 PPTX 转成 Markdown，并抽取图片。

    - Markdown 文件：out_md_path
    - 图片目录：与 md 同级，名为 `<md_stem>_media/`
    """
    _safe_mkdir(out_md_path.parent)
    media_dir = out_md_path.parent / f"{out_md_path.stem}_media"
    _safe_mkdir(media_dir)

    with zipfile.ZipFile(in_path, "r") as zf:
        slide_members: List[Tuple[int, str]] = []
        for name in zf.namelist():
            m = re.fullmatch(r"ppt/slides/slide(\d+)\.xml", name)
            if m:
                slide_members.append((int(m.group(1)), name))
        slide_members.sort(key=lambda x: x[0])

        md_lines: List[str] = []
        title = in_path.stem
        md_lines.append(f"# {title}")
        md_lines.append("")
        md_lines.append(f"- 源文件：`{in_path}`")
        md_lines.append("")

        extracted_images: set[str] = set()
        for slide_idx, slide_member in slide_members:
            slide_xml = _read_zip_text(zf, slide_member)
            paras = _extract_pptx_slide_text(slide_xml)
            img_targets = _pptx_slide_image_targets(zf, slide_idx)

            md_lines.append(f"## Slide {slide_idx}")
            md_lines.append("")
            if paras:
                for p in paras:
                    md_lines.append(p)
                    md_lines.append("")
            else:
                md_lines.append("_（未提取到可见文字，可能主要是图片/公式/图表）_")
                md_lines.append("")

            if img_targets:
                md_lines.append("**本页图片（已抽取）**")
                md_lines.append("")
                for tgt in img_targets:
                    fname = posixpath.basename(tgt)
                    out_img = media_dir / fname
                    if tgt not in extracted_images:
                        # 只复制一次
                        with zf.open(tgt, "r") as src, open(out_img, "wb") as dst:
                            shutil.copyfileobj(src, dst)
                        extracted_images.add(tgt)
                    md_lines.append(f"![]({media_dir.name}/{fname})")
                    md_lines.append("")

        # 如果没有任何 slide（异常 pptx），仍然输出一个空 md 以便定位问题
        if not slide_members:
            md_lines.append("_（未找到 slide XML，PPTX 结构可能异常）_")
            md_lines.append("")

    out_md_path.write_text("\n".join(md_lines), encoding="utf-8")


def preprocess_ipynb(in_path: Path, out_py_path: Path, out_md_path: Optional[Path]) -> None:
    """将 ipynb 转为 .py（+可选 .md）。"""
    try:
        import nbformat
    except Exception as e:  # pragma: no cover
        raise RuntimeError("缺少依赖 nbformat，无法转换 .ipynb。请先安装 nbformat。") from e

    _safe_mkdir(out_py_path.parent)
    if out_md_path is not None:
        _safe_mkdir(out_md_path.parent)

    nb = nbformat.read(str(in_path), as_version=4)

    py_lines: List[str] = []
    py_lines.append("# -*- coding: utf-8 -*-")
    # 这里用三引号块注释，便于保留来源信息（而不是写成一堆 # 注释）。
    py_lines.append('"""由 ipynb 导出（预处理产物，可读化用）')
    py_lines.append("")
    py_lines.append(f"源文件：{in_path}")
    py_lines.append('"""')
    py_lines.append("")

    md_lines: List[str] = []
    if out_md_path is not None:
        md_lines.append(f"# {in_path.stem}")
        md_lines.append("")
        md_lines.append(f"- 源文件：`{in_path}`")
        md_lines.append("")

    for cell in nb.cells:
        ctype = cell.get("cell_type", "")
        source = cell.get("source", "") or ""
        source = source.rstrip()
        if not source:
            continue

        if ctype == "markdown":
            py_lines.append("# %% [markdown]")
            for line in source.splitlines():
                # 兼容空行
                if line.strip():
                    py_lines.append("# " + line)
                else:
                    py_lines.append("#")
            py_lines.append("")

            if out_md_path is not None:
                md_lines.append(source)
                md_lines.append("")
        elif ctype == "code":
            py_lines.append("# %%")
            py_lines.extend(source.splitlines())
            py_lines.append("")

            if out_md_path is not None:
                md_lines.append("```python")
                md_lines.append(source)
                md_lines.append("```")
                md_lines.append("")
        else:
            # raw/unknown：写到 py 注释里，避免丢信息
            py_lines.append("# %% [raw]")
            for line in source.splitlines():
                py_lines.append("# " + line)
            py_lines.append("")

    out_py_path.write_text("\n".join(py_lines), encoding="utf-8")
    if out_md_path is not None:
        out_md_path.write_text("\n".join(md_lines), encoding="utf-8")


def preprocess_pdf_to_text(in_path: Path, out_txt_path: Path) -> bool:
    """使用系统 pdftotext 把 PDF 转成 txt；成功返回 True。"""
    pdftotext = shutil.which("pdftotext")
    if not pdftotext:
        return False
    _safe_mkdir(out_txt_path.parent)
    # -layout：尽量保留排版；-nopgbrk：不插入分页符（可读性更好）
    cmd = [pdftotext, "-layout", "-nopgbrk", str(in_path), str(out_txt_path)]
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except subprocess.CalledProcessError:
        return False
    return True


@dataclass(frozen=True)
class ConvertResult:
    kind: str
    src: Path
    dst: Path
    ok: bool
    note: str = ""


def _iter_files(root: Path, suffixes: Sequence[str]) -> Iterable[Path]:
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if p.suffix.lower() in suffixes:
            yield p


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="preprocess_7_ml_cases",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description=textwrap.dedent(
            """\
            把“7-机器学习实战案例及代码”里的 PPTX/IPYNB/PDF 预处理为可读文本格式。

            默认输出到：mcm_temp/preprocessed/7-机器学习实战案例及代码/
            """
        ),
    )
    parser.add_argument(
        "--input-root",
        default="7-机器学习实战案例及代码",
        help="输入根目录（默认：7-机器学习实战案例及代码）",
    )
    parser.add_argument(
        "--output-root",
        default="mcm_temp/preprocessed/7-机器学习实战案例及代码",
        help="输出根目录（默认：mcm_temp/preprocessed/7-机器学习实战案例及代码）",
    )
    parser.add_argument("--no-pptx", action="store_true", help="跳过 PPTX 处理")
    parser.add_argument("--no-ipynb", action="store_true", help="跳过 IPYNB 处理")
    parser.add_argument("--no-pdf", action="store_true", help="跳过 PDF 处理")
    parser.add_argument(
        "--ipynb-md",
        action="store_true",
        help="同时为 ipynb 生成 .md（默认只生成 .py）",
    )

    args = parser.parse_args(argv)

    in_root = Path(args.input_root)
    out_root = Path(args.output_root)

    if not in_root.exists():
        print(f"[ERROR] 输入目录不存在：{in_root}", file=sys.stderr)
        return 2

    results: List[ConvertResult] = []

    if not args.no_pptx:
        for src in _iter_files(in_root, [".pptx"]):
            rel = Path(_rel_to(in_root, src))
            dst = (out_root / rel).with_suffix(".md")
            try:
                preprocess_pptx(src, dst)
                results.append(ConvertResult("pptx->md", src, dst, True))
            except Exception as e:
                results.append(ConvertResult("pptx->md", src, dst, False, note=str(e)))

    if not args.no_ipynb:
        for src in _iter_files(in_root, [".ipynb"]):
            rel = Path(_rel_to(in_root, src))
            dst_py = (out_root / rel).with_suffix(".py")
            dst_md = (out_root / rel).with_suffix(".md") if args.ipynb_md else None
            try:
                preprocess_ipynb(src, dst_py, dst_md)
                results.append(ConvertResult("ipynb->py", src, dst_py, True))
                if dst_md is not None:
                    results.append(ConvertResult("ipynb->md", src, dst_md, True))
            except Exception as e:
                results.append(ConvertResult("ipynb", src, dst_py, False, note=str(e)))

    if not args.no_pdf:
        for src in _iter_files(in_root, [".pdf"]):
            rel = Path(_rel_to(in_root, src))
            dst = (out_root / rel).with_suffix(".txt")
            ok = preprocess_pdf_to_text(src, dst)
            results.append(
                ConvertResult(
                    "pdf->txt",
                    src,
                    dst,
                    ok,
                    note="" if ok else "pdftotext 失败或不可用",
                )
            )

    ok_n = sum(1 for r in results if r.ok)
    fail_n = sum(1 for r in results if not r.ok)

    print(f"[DONE] ok={ok_n} fail={fail_n} output_root={out_root}")
    if fail_n:
        print("[FAILED LIST]")
        for r in results:
            if r.ok:
                continue
            print(f"- {r.kind}: {r.src} -> {r.dst} ({r.note})")

    return 0 if fail_n == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
