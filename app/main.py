from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup, NavigableString, Comment
from fastapi import BackgroundTasks
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from opencc import OpenCC


EPUB_MEDIA_TYPE = "application/epub+zip"
TEXT_FILE_SUFFIXES = {".xhtml", ".html", ".htm", ".xml", ".ncx", ".opf"}
SKIP_TAGS = {"script", "style"}

app = FastAPI(title="EPUB 繁转简服务")
converter = OpenCC("tw2sp")


def _safe_extract_epub(epub_path: Path, output_dir: Path) -> None:
    with zipfile.ZipFile(epub_path, "r") as archive:
        for member in archive.infolist():
            member_path = output_dir / member.filename
            resolved_path = member_path.resolve()
            if not str(resolved_path).startswith(str(output_dir.resolve())):
                raise HTTPException(status_code=400, detail="EPUB 文件包含非法路径。")
            archive.extract(member, output_dir)


def _iter_epub_text_files(root_dir: Path) -> Iterable[Path]:
    for path in root_dir.rglob("*"):
        if path.is_file() and path.suffix.lower() in TEXT_FILE_SUFFIXES:
            yield path


def _convert_html_like_file(file_path: Path) -> None:
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
        if converted != text_node:
            text_node.replace_with(NavigableString(converted))

    file_path.write_text(str(soup), encoding="utf-8")


def _repack_epub(source_dir: Path, output_file: Path) -> None:
    mimetype_path = source_dir / "mimetype"
    if not mimetype_path.exists():
        raise HTTPException(status_code=400, detail="EPUB 缺少 mimetype 文件。")

    with zipfile.ZipFile(output_file, "w") as archive:
        archive.write(mimetype_path, "mimetype", compress_type=zipfile.ZIP_STORED)
        for path in sorted(source_dir.rglob("*")):
            if not path.is_file() or path == mimetype_path:
                continue
            archive.write(path, path.relative_to(source_dir), compress_type=zipfile.ZIP_DEFLATED)


def convert_epub_to_simplified(input_path: Path, output_path: Path) -> None:
    with tempfile.TemporaryDirectory() as temp_dir:
        work_dir = Path(temp_dir)
        extract_dir = work_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        _safe_extract_epub(input_path, extract_dir)

        for text_file in _iter_epub_text_files(extract_dir):
            _convert_html_like_file(text_file)

        _repack_epub(extract_dir, output_path)


@app.get("/", response_class=HTMLResponse)
async def index() -> str:
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>EPUB 繁转简</title>
      <style>
        :root {
          color-scheme: light;
          --bg: #f3efe6;
          --panel: #fffaf2;
          --line: #d9c8aa;
          --text: #30261b;
          --accent: #8b5e34;
          --accent-2: #b57f50;
        }
        * { box-sizing: border-box; }
        body {
          margin: 0;
          font-family: "PingFang SC", "Noto Serif SC", serif;
          background:
            radial-gradient(circle at top, rgba(181, 127, 80, 0.18), transparent 28%),
            linear-gradient(180deg, #f7f1e5 0%, var(--bg) 100%);
          color: var(--text);
          min-height: 100vh;
          display: grid;
          place-items: center;
          padding: 24px;
        }
        .card {
          width: min(680px, 100%);
          background: rgba(255, 250, 242, 0.92);
          border: 1px solid var(--line);
          border-radius: 24px;
          box-shadow: 0 20px 60px rgba(89, 62, 24, 0.12);
          padding: 32px;
          backdrop-filter: blur(10px);
        }
        h1 {
          margin: 0 0 12px;
          font-size: clamp(2rem, 4vw, 3rem);
        }
        p {
          line-height: 1.7;
          margin: 0 0 20px;
        }
        form {
          display: grid;
          gap: 16px;
        }
        input[type="file"] {
          width: 100%;
          border: 1px dashed var(--line);
          border-radius: 16px;
          padding: 18px;
          background: #fff;
        }
        button {
          border: 0;
          border-radius: 999px;
          padding: 14px 20px;
          font-size: 1rem;
          color: #fff;
          background: linear-gradient(135deg, var(--accent), var(--accent-2));
          cursor: pointer;
        }
        .tip {
          font-size: 0.92rem;
          color: #5f4d39;
        }
      </style>
    </head>
    <body>
      <main class="card">
        <h1>繁体 EPUB 转简体 EPUB</h1>
        <p>上传一本繁体中文 EPUB，服务会用 OpenCC 转换正文文本，并把新的简体 EPUB 直接返回给你。</p>
        <form action="/convert" enctype="multipart/form-data" method="post">
          <input accept=".epub,application/epub+zip" name="file" required type="file" />
          <button type="submit">开始转换</button>
        </form>
        <p class="tip">当前会转换 EPUB 内的 XHTML、HTML、OPF、NCX、XML 文本内容，并保留原始图片与资源文件。</p>
      </main>
    </body>
    </html>
    """


@app.post("/convert")
async def convert(background_tasks: BackgroundTasks, file: UploadFile = File(...)) -> FileResponse:
    if not file.filename or not file.filename.lower().endswith(".epub"):
        raise HTTPException(status_code=400, detail="请上传 .epub 文件。")

    temp_dir = Path(tempfile.mkdtemp(prefix="epub-convert-"))
    input_path = temp_dir / file.filename
    output_name = f"{Path(file.filename).stem}.simplified.epub"
    output_path = temp_dir / output_name

    with input_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    await file.close()

    try:
        convert_epub_to_simplified(input_path, output_path)
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=400, detail="上传的文件不是有效的 EPUB。") from exc

    background_tasks.add_task(shutil.rmtree, temp_dir, ignore_errors=True)

    return FileResponse(
        path=output_path,
        media_type=EPUB_MEDIA_TYPE,
        filename=output_name,
    )


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
