# Log Viewer

JSON / YAML ログファイルをブラウザで閲覧・検索するためのツール。

## Tech Stack

- **FastAPI** — バックエンド API
- **Jinja2** — テンプレートエンジン
- **htmx** — SPA 風インタラクション
- **Tailwind CSS + DaisyUI** — UI スタイリング

## Setup

```bash
cd log-viewer
pip install -r requirements.txt
```

## Usage

```bash
# デフォルト (sample_logs ディレクトリを表示)
uvicorn main:app --reload

# 任意のログディレクトリを指定
LOG_DIR=/path/to/logs uvicorn main:app --reload
```

ブラウザで http://localhost:8000 を開く。

## Features

- JSON / YAML ログファイルの一覧表示
- テーブル形式でのレコード表示
- キーワード検索
- ログレベルフィルタ (DEBUG / INFO / WARNING / ERROR / CRITICAL)
- レコード詳細表示 (モーダル)
- ファイルアップロード
