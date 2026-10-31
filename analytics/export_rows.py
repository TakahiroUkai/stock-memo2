#!/usr/bin/env python3
"""data/analytics.json を、ダッシュボード用の3つの行データ(JSON配列)に変換する。

使い方: python3 analytics/export_rows.py <出力フォルダ>
  → sites.json(サイト別の直近30日合計) / daily.json(日別) / pages.json(人気ページ)
"""
import json
import os
import sys

SRC = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.json")
out = sys.argv[1] if len(sys.argv) > 1 else "."
d = json.load(open(SRC, encoding="utf8"))
sites, daily, pages = [], [], []
for s in d["sites"]:
    sites.append({"site": s["name"], **s["last30"]})
    for r in s["daily"]:
        daily.append({"date": r["date"], "site": s["name"], "views": r["views"],
                      "users": r["users"], "sessions": r["sessions"]})
    for p in s["top_pages"]:
        pages.append({"site": s["name"], "path": p["path"], "title": p["title"],
                      "views": p["views"], "users": p["users"]})
os.makedirs(out, exist_ok=True)
for name, rows in (("sites", sites), ("daily", daily), ("pages", pages)):
    with open(os.path.join(out, name + ".json"), "w", encoding="utf8") as f:
        json.dump(rows, f, ensure_ascii=False)
print("updated_at:", d["updated_at"], "| sites", len(sites), "daily", len(daily), "pages", len(pages))
