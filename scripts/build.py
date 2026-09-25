"""Read the Notion 中控台 database and write data.json for the control center page."""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

NOTION_TOKEN = os.environ.get("NOTION_TOKEN")
DATA_SOURCE_ID = os.environ.get("NOTION_DATA_SOURCE_ID", "bc8ef4a5-2a0b-40a1-8563-c5c58045af69")
OUT = "data.json"

if not NOTION_TOKEN:
    print("NOTION_TOKEN missing; leaving data.json unchanged")
    sys.exit(0)

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2025-09-03",
    "Content-Type": "application/json",
}


def query(cursor=None):
    body = {"page_size": 100}
    if cursor:
        body["start_cursor"] = cursor
    req = urllib.request.Request(
        f"https://api.notion.com/v1/data_sources/{DATA_SOURCE_ID}/query",
        data=json.dumps(body).encode(),
        headers=HEADERS,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def text(prop):
    if not prop:
        return ""
    t = prop.get("type")
    if t == "title":
        return "".join(x["plain_text"] for x in prop["title"])
    if t == "rich_text":
        return "".join(x["plain_text"] for x in prop["rich_text"])
    if t == "select":
        return (prop["select"] or {}).get("name", "")
    if t == "status":
        return (prop["status"] or {}).get("name", "")
    if t == "url":
        return prop["url"] or ""
    if t == "date":
        return (prop["date"] or {}).get("start", "") or ""
    return ""


def flag(p, name):
    return bool((p.get(name) or {}).get("checkbox"))


rows = []
cursor = None
while True:
    res = query(cursor)
    for page in res.get("results", []):
        p = page["properties"]
        rows.append({
            "id": page["id"].replace("-", ""),
            "n": (p.get("集數") or {}).get("number") or 0,
            "title": text(p.get("影片標題")),
            "framework": text(p.get("借用框架")),
            "groups": [o["name"] for o in (p.get("主要族群") or {}).get("multi_select", [])],
            "line": text(p.get("內容線")),
            "status": text(p.get("狀態")),
            "scriptState": text(p.get("講稿狀態")),
            "youtube": text(p.get("YouTube 連結")),
            "publishDate": text(p.get("預計發布日")),
            "flags": [
                flag(p, "講稿完成"),
                flag(p, "拍攝完成"),
                flag(p, "剪輯完成"),
                flag(p, "封面完成"),
                flag(p, "標題與資訊欄完成"),
                flag(p, "已上架"),
            ],
            "shorts": flag(p, "短影音已切"),
        })
    if not res.get("has_more"):
        break
    cursor = res.get("next_cursor")

rows.sort(key=lambda r: r["n"])
tw = timezone(timedelta(hours=8))
payload = {"updated": datetime.now(tw).strftime("%Y/%m/%d %H:%M"), "videos": rows}
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(payload, f, ensure_ascii=False, indent=1)
print(f"wrote {OUT} with {len(rows)} rows")
