---
name: epub-opencc-convert
description: Convert Traditional Chinese EPUB files into Simplified Chinese EPUB files with OpenCC while preserving the original EPUB structure and assets. Use when Codex receives a local `.epub` file and the user asks to convert 繁体 to 简体, 繁轉簡, zh-TW to zh-CN, or requests a new simplified `.epub` output instead of plain text extraction.
---

# EPUB OpenCC Convert

Convert the user's local EPUB file into a new Simplified Chinese EPUB by running the bundled script.

## Workflow

1. Confirm the input is a local `.epub` file.
2. Prefer the bundled script at `scripts/convert_epub.py` over rewriting EPUB logic in the conversation.
3. Keep the default OpenCC config as `tw2sp` unless the user explicitly asks for another conversion preset.
4. Write the output next to the source file with the suffix `.simplified.epub` unless the user asks for a different path.
5. Report the output path clearly.

## Command

Run:

```bash
python3 /path/to/skill/scripts/convert_epub.py /absolute/path/to/input.epub
```

Optional flags:

- `--output /absolute/path/to/output.epub`
- `--config tw2sp`
- `--force`

## Constraints

- Reject non-EPUB inputs instead of guessing conversions from other formats.
- Preserve images, fonts, stylesheets, and non-text assets.
- Convert text-bearing EPUB files only: `.xhtml`, `.html`, `.htm`, `.xml`, `.ncx`, `.opf`.
- Skip text inside `script` and `style` tags.

## Failure Handling

- If the file is not a valid EPUB archive, stop and report that clearly.
- If the output path already exists, overwrite only when the user explicitly asks; otherwise choose a non-conflicting path or ask.
- If dependencies are missing, install `opencc-python-reimplemented`, `beautifulsoup4`, and `lxml` before retrying.
