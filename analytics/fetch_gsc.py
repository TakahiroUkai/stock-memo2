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
import re
import socket
import sys
import time
import urllib.request
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
socket.setdefaulttimeout(30)  # 応答が返らないまま止まらないように
INSPECT_LIMIT = 200   # 1サイトあたり、登録状況を調べるページ数の上限(API の上限は1サイト1日2000回)
INSPECT_BUDGET = 90    # 1サイトあたりの制限時間(秒)。超えたらそこまでの分で打ち切る
INSPECT_SLEEP = 0.2   # 1回ごとの待ち(秒)
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


def sitemap_urls(site_url):
    """公開中の sitemap.xml から、ページのURLの一覧を読む。"""
    with urllib.request.urlopen(site_url + "sitemap.xml", timeout=30) as r:
        xml = r.read().decode("utf8", "replace")
    return re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml)


def inspect_index(svc, site_url):
    """URL検査 API で、sitemap のページが Google に登録(インデックス)されているかを数える。"""
    urls = sitemap_urls(site_url)
    todo = urls[:INSPECT_LIMIT]
    states, not_indexed, indexed, checked, stopped = {}, [], 0, 0, None
    t0 = time.time()
    for u in todo:
        if time.time() - t0 > INSPECT_BUDGET:
            stopped = f"時間切れ({INSPECT_BUDGET}秒)"
            break
        try:
            body = {"inspectionUrl": u, "siteUrl": site_url, "languageCode": "ja"}
            r = svc.urlInspection().index().inspect(body=body).execute()
            st = r.get("inspectionResult", {}).get("indexStatusResult", {})
        except Exception as e:  # 上限超過など。ここまでの分で打ち切る
            stopped = f"{type(e).__name__}: {str(e)[:160]}"
            break
        checked += 1
        state = st.get("coverageState") or st.get("verdict") or "不明"
        states[state] = states.get(state, 0) + 1
        if st.get("verdict") == "PASS":
            indexed += 1
        elif len(not_indexed) < 5:
            not_indexed.append({"url": u, "state": state})
        time.sleep(INSPECT_SLEEP)
    out = {"total": len(urls), "checked": checked, "indexed": indexed,
           "states": states, "not_indexed_sample": not_indexed}
    if stopped:
        out["stopped"] = stopped
    return out


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
    res = {**site, "last28": total, "daily": daily, "top_pages": pages,
           "top_queries": queries, "sitemaps": sitemaps}
    try:  # 登録状況の取得に失敗しても、ほかの数字は残す
        res["index"] = inspect_index(svc, url)
    except Exception as e:
        res["index_error"] = f"{type(e).__name__}: {str(e)[:200]}"
    return res


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
            ix = s.get("index")
            extra = f" 登録済み: {ix['indexed']}/{ix['total']}" if ix else f" 登録状況: 取得できず({s.get('index_error', '')[:60]})"
            print(s["key"], f"{start}〜{end} 表示:", s["last28"]["impressions"], "クリック:", s["last28"]["clicks"], extra)
    if failed == len(SITES):
        sys.exit("4サイトとも取得できませんでした")


if __name__ == "__main__":
    main()
