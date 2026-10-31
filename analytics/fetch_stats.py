#!/usr/bin/env python3
"""GA4 Data API から3サイト分のアクセス数を取得し、data/analytics.json に保存する。

認証: 環境変数 GA_KEY にサービスアカウントのJSONキー(文字列)を入れる。
      (GitHub の Secrets に登録。リポジトリにはコミットしない)
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange, Dimension, Filter, FilterExpression, Metric, OrderBy, RunReportRequest,
)

PROPERTY_ID = os.environ.get("GA_PROPERTY_ID", "384833511")
OUT = os.path.join(os.path.dirname(__file__), "..", "data", "analytics.json")

# 3サイトの見分け方: URLの最初のパス(リポジトリ名)
SITES = [
    {"key": "stock", "name": "投資銘柄ピックアップ(注目銘柄メモ)", "path": "/stock-memo2/"},
    {"key": "claude", "name": "Claudeあれこれ(あんなことこんなことClaude)", "path": "/anna-konna-claude/"},
    {"key": "kasegi", "name": "稼ぎ方トリセツ(稼ぎのトリセツ)", "path": "/kasegi-torisetsu/"},
]
DAILY_RANGE = "89daysAgo"   # 日別は直近90日
TOP_RANGE = "29daysAgo"     # ページ別は直近30日


def path_filter(path):
    return FilterExpression(filter=Filter(
        field_name="pagePath",
        string_filter=Filter.StringFilter(
            match_type=Filter.StringFilter.MatchType.BEGINS_WITH, value=path),
    ))


def ymd(s):
    return f"{s[:4]}-{s[4:6]}-{s[6:]}"


def run(client, **kw):
    req = RunReportRequest(property=f"properties/{PROPERTY_ID}", **kw)
    return client.run_report(req)


def fetch_site(client, site):
    flt = path_filter(site["path"])
    daily_resp = run(
        client,
        dimensions=[Dimension(name="date")],
        metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers"), Metric(name="sessions")],
        date_ranges=[DateRange(start_date=DAILY_RANGE, end_date="today")],
        dimension_filter=flt,
        order_bys=[OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="date"))],
        limit=1000,
    )
    daily = [
        {"date": ymd(r.dimension_values[0].value),
         "views": int(r.metric_values[0].value),
         "users": int(r.metric_values[1].value),
         "sessions": int(r.metric_values[2].value)}
        for r in daily_resp.rows
    ]
    top_resp = run(
        client,
        dimensions=[Dimension(name="pagePath"), Dimension(name="pageTitle")],
        metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers")],
        date_ranges=[DateRange(start_date=TOP_RANGE, end_date="today")],
        dimension_filter=flt,
        order_bys=[OrderBy(metric=OrderBy.MetricOrderBy(metric_name="screenPageViews"), desc=True)],
        limit=30,
    )
    top = [
        {"path": r.dimension_values[0].value,
         "title": r.dimension_values[1].value,
         "views": int(r.metric_values[0].value),
         "users": int(r.metric_values[1].value)}
        for r in top_resp.rows
    ]
    # 期間合計(サイト全体のユーザー数は、日別の合算だと重複するので別に取る)
    tot_resp = run(
        client,
        metrics=[Metric(name="screenPageViews"), Metric(name="activeUsers"), Metric(name="sessions")],
        date_ranges=[DateRange(start_date=TOP_RANGE, end_date="today")],
        dimension_filter=flt,
    )
    if tot_resp.rows:
        v = tot_resp.rows[0].metric_values
        last30 = {"views": int(v[0].value), "users": int(v[1].value), "sessions": int(v[2].value)}
    else:
        last30 = {"views": 0, "users": 0, "sessions": 0}
    return {**site, "last30": last30, "daily": daily, "top_pages": top}


def main():
    key = os.environ.get("GA_KEY", "").strip()
    if not key:
        sys.exit("GA_KEY が設定されていません(GitHub の Secrets に登録してください)")
    client = BetaAnalyticsDataClient.from_service_account_info(json.loads(key))
    jst = timezone(timedelta(hours=9))
    result = {
        "updated_at": datetime.now(jst).strftime("%Y-%m-%d %H:%M JST"),
        "sites": [fetch_site(client, s) for s in SITES],
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
        f.write("\n")
    for s in result["sites"]:
        print(s["key"], "直近30日 views:", s["last30"]["views"], "users:", s["last30"]["users"])


if __name__ == "__main__":
    main()
