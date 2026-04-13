# 中文 EPUB 繁转简服务

上传一个繁体中文 EPUB，服务会调用 OpenCC 把 EPUB 内的文本内容转成简体中文，并返回新的 EPUB 文件。

## 功能

- 上传 `.epub` 文件
- 使用 OpenCC `tw2sp` 配置做繁体转简体
- 保留 EPUB 内的图片、样式、字体等资源
- 返回转换后的 `.simplified.epub`

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
