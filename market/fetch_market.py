#!/usr/bin/env python3
"""日本株の株価・指標・業績を yfinance(Yahoo Finance)から取得し、銘柄ごとのJSONに保存する。

使い方: python3 market/fetch_market.py OUT_DIR [コード ...]
  コードを省くと market/watchlist.txt の銘柄を使う。
出力: OUT_DIR/<コード>.json と OUT_DIR/index.json
  index.json の stale が true の銘柄は、株価の基準日が古い(直近の営業日から2営業日以上前)。
  その値は「最新」として使わない(定期タスクの規則)。
注意: yfinance は非公式です。値は決算短信などで確かめること。取れない項目は null のまま残し、推測で埋めない。
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

JST = timezone(timedelta(hours=9))
INFO_KEYS = [
    "longName", "shortName", "sector", "industry", "exchange", "currency",
    "currentPrice", "regularMarketPrice", "previousClose",
    "trailingPE", "forwardPE", "priceToBook", "trailingEps", "forwardEps", "bookValue",
    "dividendRate", "dividendYield", "trailingAnnualDividendRate", "payoutRatio",
    "marketCap", "sharesOutstanding", "fiftyTwoWeekHigh", "fiftyTwoWeekLow",
    "returnOnEquity", "longBusinessSummary",
]
STMT_ROWS = ["Total Revenue", "Operating Income", "Pretax Income", "Net Income", "Basic EPS"]


def business_days_between(d1, d2):
    """d1 から d2 までの平日の数(祝日は考慮しない。d1<d2)。"""
    n, d = 0, d1
    while d < d2:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n += 1
    return n


def num(x):
    try:
        v = float(x)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def fetch_one(code, now):
    import yfinance as yf
    t = yf.Ticker(f"{code}.T")
    out = {"code": code, "ticker": f"{code}.T", "fetched_at_jst": now.isoformat(timespec="seconds"),
           "source": "yfinance(Yahoo Finance、非公式)", "errors": []}
    try:
        info = t.info or {}
    except Exception as e:  # noqa: BLE001
        info, _ = {}, out["errors"].append(f"info: {e}")
    out["info"] = {k: info.get(k) for k in INFO_KEYS}
    # 直近の終値と、その日付(基準日)
    try:
        h = t.history(period="10d", interval="1d", auto_adjust=False)
        if len(h):
            last = h.iloc[-1]
            out["price_date"] = h.index[-1].date().isoformat()
            out["close"] = num(last["Close"])
            out["volume"] = num(last["Volume"])
            out["recent_closes"] = [{"date": i.date().isoformat(), "close": num(r["Close"])} for i, r in h.tail(5).iterrows()]
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"history: {e}")
    # 年間業績(決算期ごと)
    try:
        st = t.income_stmt
        fin = {}
        if st is not None and len(st):
            for col in st.columns:
                key = str(col.date())
                fin[key] = {r: num(st.loc[r, col]) for r in STMT_ROWS if r in st.index}
        out["annual"] = fin
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"income_stmt: {e}")
    # 配当(年ごとの合計)
    try:
        dv = t.dividends
        out["dividends_by_year"] = {} if dv is None or not len(dv) else \
            {str(y): round(float(v), 2) for y, v in dv.groupby(dv.index.year).sum().items()}
    except Exception as e:  # noqa: BLE001
        out["errors"].append(f"dividends: {e}")
    # 派生値と古さの判定
    px = out.get("close")
    rate = out["info"].get("dividendRate")
    out["derived"] = {
        "min_purchase_yen_100sh": None if px is None else round(px * 100),
        "dividend_yield_pct_from_rate": None if not (px and rate) else round(rate / px * 100, 2),
    }
    if out.get("price_date"):
        pd_ = datetime.fromisoformat(out["price_date"]).date()
        gap = business_days_between(pd_, now.date())
        out["business_days_old"] = gap
        out["stale"] = gap >= 2
    else:
        out["stale"] = True
        out["errors"].append("株価の基準日が取れませんでした")
    out["ok"] = out.get("close") is not None and not out["stale"]
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out_dir = sys.argv[1]
    codes = sys.argv[2:]
    if not codes:
        wl = os.path.join(os.path.dirname(__file__), "watchlist.txt")
        codes = [ln.split("#")[0].strip() for ln in open(wl, encoding="utf8")]
    codes = [c for c in dict.fromkeys(c.strip() for c in codes) if c]
    if not codes:
        print("取得する銘柄がありません(watchlist.txt が空で、コードの指定もありません)")
        return
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.now(JST)
    index = {"generated_at_jst": now.isoformat(timespec="seconds"), "items": []}
    for c in codes:
        try:
            r = fetch_one(c, now)
        except Exception as e:  # noqa: BLE001
            r = {"code": c, "ok": False, "stale": True, "errors": [f"fetch: {e}"], "fetched_at_jst": now.isoformat(timespec="seconds")}
        json.dump(r, open(os.path.join(out_dir, f"{c}.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
        index["items"].append({"code": c, "ok": r["ok"], "price_date": r.get("price_date"), "close": r.get("close"),
                               "stale": r["stale"], "errors": r["errors"]})
        print(c, "ok" if r["ok"] else "NG", r.get("price_date"), r.get("close"), r["errors"])
    json.dump(index, open(os.path.join(out_dir, "index.json"), "w", encoding="utf8"), ensure_ascii=False, indent=1)
    if not any(i["ok"] for i in index["items"]):
        sys.exit("どの銘柄も最新の株価を取得できませんでした")


if __name__ == "__main__":
    main()
