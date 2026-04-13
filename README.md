# EPUB Convert

这个仓库同时提供两种形态：

- `app/`：一个上传 EPUB 并返回简体 EPUB 的 Web 服务
- `skill/`：一个可被 Codex/agent 使用的脚本型 skill

## 功能

- 上传 `.epub` 文件
- 使用 OpenCC `tw2sp` 配置做繁体转简体
- 保留 EPUB 内的图片、样式、字体等资源
- 返回转换后的 `.simplified.epub`
- 支持命令行脚本直接转换本地 EPUB 文件

## 命令行使用

安装依赖后，可以直接运行 skill 自带脚本：

```bash
python3 skill/scripts/convert_epub.py /absolute/path/to/book.epub
```

输出会是原目录下的：

```bash
/absolute/path/to/book.simplified.epub
```

也可以自定义输出路径：

```bash
python3 skill/scripts/convert_epub.py /absolute/path/to/book.epub --output /absolute/path/to/book-cn.epub
```

如果输出文件已经存在，可显式覆盖：

```bash
python3 skill/scripts/convert_epub.py /absolute/path/to/book.epub --force
```

## Skill 安装

如果你想让另一个 Codex/agent 通过 GitHub 使用这个 skill，推荐这样做：

1. 拉取仓库
2. 在目标机器上创建技能目录 `${CODEX_HOME:-$HOME/.codex}/skills/epub-opencc-convert`
3. 把仓库里的 `skill/` 目录内容复制进去

示例：

```bash
git clone https://github.com/linuo/epub-convert.git
cd epub-convert
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills/epub-opencc-convert"
cp -R skill/. "${CODEX_HOME:-$HOME/.codex}/skills/epub-opencc-convert/"
```

安装后，agent 在遇到“把繁体 EPUB 转成简体 EPUB”这类请求时，就可以触发这个 skill。

## 启动

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

启动后访问 <http://127.0.0.1:8000>。

## 接口

### `GET /`

打开上传页面。

### `POST /convert`

表单字段：

- `file`: EPUB 文件

返回值：

- 转换后的 EPUB 文件下载流

### `GET /health`

健康检查接口。
