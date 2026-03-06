import json
import os
from pathlib import Path
from typing import Optional

import yaml
from fastapi import FastAPI, Query, Request, UploadFile, File
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

app = FastAPI(title="Log Viewer")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"
SAMPLE_LOGS_DIR = BASE_DIR / "sample_logs"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Configurable log directory (default: sample_logs)
LOG_DIR = Path(os.environ.get("LOG_DIR", str(SAMPLE_LOGS_DIR)))


def _parse_file(file_path: Path) -> dict:
    """Parse a JSON or YAML log file and return structured data."""
    suffix = file_path.suffix.lower()
    text = file_path.read_text(encoding="utf-8")

    if suffix == ".json":
        data = json.loads(text)
    elif suffix in (".yaml", ".yml"):
        data = yaml.safe_load(text)
    else:
        return {"error": f"Unsupported file type: {suffix}"}

    # Normalise to list of records
    if isinstance(data, dict):
        data = [data]
    elif not isinstance(data, list):
        data = [{"value": data}]

    return {"records": data, "count": len(data)}


def _list_log_files(directory: Path) -> list[dict]:
    """List all JSON/YAML files in the given directory."""
    files = []
    if not directory.exists():
        return files
    for p in sorted(directory.iterdir()):
        if p.is_file() and p.suffix.lower() in (".json", ".yaml", ".yml"):
            files.append({
                "name": p.name,
                "path": str(p),
                "size": p.stat().st_size,
                "suffix": p.suffix.lower(),
            })
    return files


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    files = _list_log_files(LOG_DIR)
    return templates.TemplateResponse("index.html", {
        "request": request,
        "files": files,
        "log_dir": str(LOG_DIR),
    })


# ---------------------------------------------------------------------------
# HTMX partials
# ---------------------------------------------------------------------------

@app.get("/view", response_class=HTMLResponse)
async def view_file(
    request: Request,
    file: str = Query(..., description="File name to view"),
    search: Optional[str] = Query(None, description="Search keyword"),
    level: Optional[str] = Query(None, description="Log level filter"),
):
    file_path = LOG_DIR / file
    if not file_path.exists() or not file_path.is_file():
        return HTMLResponse("<div class='alert alert-error'>File not found</div>")

    parsed = _parse_file(file_path)
    if "error" in parsed:
        return HTMLResponse(f"<div class='alert alert-error'>{parsed['error']}</div>")

    records = parsed["records"]

    # Filter by log level
    if level and level != "all":
        records = [
            r for r in records
            if str(r.get("level", r.get("severity", ""))).lower() == level.lower()
        ]

    # Search filter
    if search:
        search_lower = search.lower()
        records = [
            r for r in records
            if search_lower in json.dumps(r, ensure_ascii=False, default=str).lower()
        ]

    return templates.TemplateResponse("partials/log_table.html", {
        "request": request,
        "records": records,
        "total": parsed["count"],
        "filtered": len(records),
        "filename": file,
    })


@app.get("/detail", response_class=HTMLResponse)
async def detail(request: Request, file: str, index: int):
    file_path = LOG_DIR / file
    if not file_path.exists():
        return HTMLResponse("<div class='alert alert-error'>File not found</div>")

    parsed = _parse_file(file_path)
    records = parsed.get("records", [])
    if index < 0 or index >= len(records):
        return HTMLResponse("<div class='alert alert-error'>Record not found</div>")

    record = records[index]
    formatted = json.dumps(record, indent=2, ensure_ascii=False, default=str)

    return templates.TemplateResponse("partials/log_detail.html", {
        "request": request,
        "record": record,
        "formatted": formatted,
        "index": index,
        "filename": file,
    })


@app.post("/upload", response_class=HTMLResponse)
async def upload_file(request: Request, file: UploadFile = File(...)):
    if not file.filename:
        return HTMLResponse("<div class='alert alert-error'>No file selected</div>")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".json", ".yaml", ".yml"):
        return HTMLResponse(
            "<div class='alert alert-error'>Unsupported file type. Use JSON or YAML.</div>"
        )

    dest = LOG_DIR / file.filename
    content = await file.read()
    dest.write_bytes(content)

    # Return updated file list
    files = _list_log_files(LOG_DIR)
    return templates.TemplateResponse("partials/file_list.html", {
        "request": request,
        "files": files,
    })
