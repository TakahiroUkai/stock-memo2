#!/usr/bin/env python3
"""Search Console から4サイト分の検索の数字を取得し、data/search_console.json に保存する。

認証: GA4 の取得(fetch_stats.py)と同じ環境変数 GA_KEY(サービスアカウントのJSONキー)を使う。
      事前に、そのサービスアカウントのメールアドレスを、各サイトの Search Console の
      「設定 → ユーザーと権限」に「制限付き」以上で追加し、Google Cloud で
      Search Console API を有効にしておく。キーはリポジトリにコミットしない。

サイトごとに取得し、失敗したサイトは error に理由を入れて続ける
(GA4 の取得とは別のファイル。失敗しても data/analytics.json には影響しない)。
Search Console の数字は、2〜3日前までの分が確定している。
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from google.oauth2 import service_account
from googleapiclient.discovery import build

OUT = os.path.join(os.path.dirname(__file__), "..", "data", "search_console.json")
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]

# URLプレフィックスのプロパティ(末尾のスラッシュまで一致させる)
SITES = [
    {"key": "stock", "name": "注目銘柄メモ", "site_url": "https://takahiroukai.github.io/stock-memo2/"},
    {"key": "claude", "name": "あんなことこんなことClaude", "site_url": "https://takahiroukai.github.io/anna-konna-claude/"},
    {"key": "kasegi", "name": "稼ぎのトリセツ", "site_url": "https://takahiroukai.github.io/kasegi-torisetsu/"},
    {"key": "tsukue", "name": "机タイム素材集", "site_url": "https://takahiroukai.github.io/tsukue-time/"},
]
DAYS = 28          # 直近28日
LAG_DAYS = 2       # 確定していない直近の日は除く


def query(svc, site_url, start, end, dimensions, limit):
    body = {"startDate": start, "endDate": end, "dimensions": dimensions, "rowLimit": limit}
    return svc.searchanalytics().query(siteUrl=site_url, body=body).execute().get("rows", [])


def row_out(r, names):
    d = {n: v for n, v in zip(names, r["keys"])}
    d.update(clicks=int(r["clicks"]), impressions=int(r["impressions"]),
             ctr=round(r["ctr"], 4), position=round(r["position"], 1))
    return d


def fetch_site(svc, site, start, end):
    url = site["site_url"]
    # 期間合計(dimensions なし)
    total_rows = query(svc, url, start, end, [], 1)
    if total_rows:
        t = total_rows[0]
        total = {"clicks": int(t["clicks"]), "impressions": int(t["impressions"]),
                 "ctr": round(t["ctr"], 4), "position": round(t["position"], 1)}
    else:
        total = {"clicks": 0, "impressions": 0, "ctr": 0, "position": 0}
    daily = [row_out(r, ["date"]) for r in query(svc, url, start, end, ["date"], 100)]
    pages = [row_out(r, ["page"]) for r in query(svc, url, start, end, ["page"], 30)]
    queries = [row_out(r, ["query"]) for r in query(svc, url, start, end, ["query"], 30)]
    # sitemap の状態(送信済みか、エラーがあるか)
    sitemaps = []
    for s in svc.sitemaps().list(siteUrl=url).execute().get("sitemap", []):
        sitemaps.append({"path": s.get("path"), "lastSubmitted": s.get("lastSubmitted"),
                         "lastDownloaded": s.get("lastDownloaded"),
                         "errors": int(s.get("errors", 0)), "warnings": int(s.get("warnings", 0)),
                         "isPending": bool(s.get("isPending", False))})
    return {**site, "last28": total, "daily": daily, "top_pages": pages,
            "top_queries": queries, "sitemaps": sitemaps}


def main():
    key = os.environ.get("GA_KEY", "").strip()
    if not key:
        sys.exit("GA_KEY が設定されていません")
    creds = service_account.Credentials.from_service_account_info(json.loads(key), scopes=SCOPES)
    svc = build("searchconsole", "v1", credentials=creds, cache_discovery=False)
    jst = timezone(timedelta(hours=9))
    today = datetime.now(jst).date()
    end = (today - timedelta(days=LAG_DAYS)).isoformat()
    start = (today - timedelta(days=LAG_DAYS + DAYS - 1)).isoformat()
    sites, failed = [], 0
    for s in SITES:
        try:
            sites.append(fetch_site(svc, s, start, end))
        except Exception as e:  # 権限がない・APIが無効など。理由だけ残して続ける
            failed += 1
            msg = f"{type(e).__name__}: {str(e)[:300]}"
            sites.append({**s, "error": msg})
            print(s["key"], "失敗:", msg)
    result = {"updated_at": datetime.now(jst).strftime("%Y-%m-%d %H:%M JST"),
              "range": {"start": start, "end": end}, "sites": sites}
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write("\n")
    for s in sites:
        if "last28" in s:
            print(s["key"], f"{start}〜{end} 表示:", s["last28"]["impressions"], "クリック:", s["last28"]["clicks"])
    if failed == len(SITES):
        sys.exit("4サイトとも取得できませんでした")


if __name__ == "__main__":
    main()
