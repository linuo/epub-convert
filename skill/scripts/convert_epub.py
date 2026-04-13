from __future__ import annotations

import argparse
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, Comment, NavigableString
from opencc import OpenCC


TEXT_FILE_SUFFIXES = {".xhtml", ".html", ".htm", ".xml", ".ncx", ".opf"}
SKIP_TAGS = {"script", "style"}


class EpubConversionError(Exception):
    """Raised when EPUB conversion cannot proceed safely."""


def _safe_extract_epub(epub_path: Path, output_dir: Path) -> None:
    with zipfile.ZipFile(epub_path, "r") as archive:
        output_root = output_dir.resolve()
        for member in archive.infolist():
            member_path = output_dir / member.filename
            resolved_path = member_path.resolve()
            if not str(resolved_path).startswith(str(output_root)):
                raise EpubConversionError("EPUB 文件包含非法路径。")
            archive.extract(member, output_dir)


def _iter_epub_text_files(root_dir: Path) -> Iterable[Path]:
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_FILE_SUFFIXES:
            yield path


def _convert_html_like_file(file_path: Path, converter: OpenCC) -> None:
    original_text = file_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(original_text, "lxml-xml")

    if soup.contents and getattr(soup.contents[0], "name", None) is None and not soup.find():
        return

    for text_node in soup.find_all(string=True):
        if isinstance(text_node, Comment):
            continue
        parent = text_node.parent
        if parent and parent.name and parent.name.lower() in SKIP_TAGS:
            continue
        converted = converter.convert(str(text_node))
        if converted != str(text_node):
            text_node.replace_with(NavigableString(converted))

    file_path.write_text(str(soup), encoding="utf-8")


def _repack_epub(source_dir: Path, output_file: Path) -> None:
    mimetype_path = source_dir / "mimetype"
    if not mimetype_path.exists():
        raise EpubConversionError("EPUB 缺少 mimetype 文件。")

    with zipfile.ZipFile(output_file, "w") as archive:
        archive.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path == mimetype_path:
                continue
            archive.write(path, path.relative_to(source_dir), compress_type=zipfile.ZIP_DEFLATED)


def default_output_path(input_path: Path) -> Path:
    return input_path.with_name(f"{input_path.stem}.simplified.epub")


def convert_epub(
    input_path: Path,
    output_path: Path | None = None,
    config: str = "tw2sp",
    force: bool = False,
) -> Path:
    if input_path.suffix.lower() != ".epub":
        raise EpubConversionError("请输入 .epub 文件。")
    if not input_path.is_file():
        raise EpubConversionError(f"找不到输入文件: {input_path}")

    resolved_input = input_path.resolve()
    resolved_output = (output_path or default_output_path(resolved_input)).resolve()
    if resolved_output.exists() and not force:
        raise EpubConversionError(f"输出文件已存在: {resolved_output}")
    converter = OpenCC(config)

    with tempfile.TemporaryDirectory() as temp_dir:
        extract_dir = Path(temp_dir) / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            _safe_extract_epub(resolved_input, extract_dir)
        except zipfile.BadZipFile as exc:
            raise EpubConversionError("输入文件不是有效的 EPUB。") from exc

        for text_file in _iter_epub_text_files(extract_dir):
            _convert_html_like_file(text_file, converter)

        _repack_epub(extract_dir, resolved_output)

    return resolved_output


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Convert Traditional Chinese EPUB to Simplified Chinese EPUB.")
    parser.add_argument("input", type=Path, help="Path to the input .epub file")
    parser.add_argument("--output", type=Path, help="Path to the output .epub file")
    parser.add_argument("--config", default="tw2sp", help="OpenCC config preset, default: tw2sp")
    parser.add_argument("--force", action="store_true", help="Overwrite the output file if it already exists")
    return parser


def main() -> int:
    parser = build_arg_parser()
    args = parser.parse_args()

    try:
        output_path = convert_epub(args.input, args.output, args.config, args.force)
    except EpubConversionError as exc:
        print(f"转换失败: {exc}")
        return 1

    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
