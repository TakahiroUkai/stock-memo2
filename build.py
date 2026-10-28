#!/usr/bin/env python3
"""data/picks.json と data/quizzes.json から静的サイト(docs/)を生成する。
毎日の更新: data/picks.json の配列の先頭に1件追加して `python3 build.py` を実行する。
記事には任意で flow(儲けの仕組みの図解)と charts(数値表に対応するグラフ)を付けられる。
公開リポジトリなので、非公開の評価データ(チェック表・特定の専門家名など)は絶対にここへ入れない。"""
import json, html, os

SITE = "注目銘柄メモ"
TAGLINE = "今は目立たないが、これから重要になりそうな日本企業の個人調査メモ"
ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, "docs")
AD_SLOT = '<aside class="ad" aria-label="広告"><!-- AdSense承認後、ここに広告コードを貼る --><span>広告枠</span></aside>'
DISC = ("本ページは個人の調査メモであり、特定の銘柄の売買を勧めるものではありません。"
        "掲載内容の正確性には注意していますが、誤りや時間の経過による変化があり得ます。"
        "投資の判断はご自身の責任で行ってください。株価などの数値は記載時点のものです。")
QUIZ_DISC = "クイズは投資用語を学ぶための教育目的のもので、特定の銘柄や売買を勧めるものではありません。"
COLORS = ["#ef9a78", "#7db5a3", "#8fa9d6"]
NG = "\u7aaa\u7530"  # 専門家名(公開データに混ざっていたら生成を止めるための安全確認)

CSS = """
:root{--bg:#fff8ef;--s:#ffffff;--fg:#4a403a;--mu:#85776c;--ln:#f0e2d0;--ac:#b5532f;--acs:#fde9d6;--gr:#e4f2ec;--gr2:#3f7d6b;--r:16px}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.85 "Zen Maru Gothic","Hiragino Maru Gothic ProN","Hiragino Sans","Noto Sans JP",sans-serif;padding:0 16px 48px}
.wrap{max-width:760px;margin:0 auto}
header{padding:24px 0 8px}header a{color:inherit;text-decoration:none}
h1{font-size:1.6rem;line-height:1.35;margin:0;font-weight:700}
.tag{color:var(--mu);font-size:.88rem;margin:4px 0 0}
nav.links{font-size:.88rem;margin:12px 0;display:flex;flex-wrap:wrap;gap:8px}
nav.links a{color:var(--ac);background:var(--s);border:1px solid var(--ln);border-radius:99px;padding:3px 14px;text-decoration:none}
.list{background:var(--s);border:1px solid var(--ln);border-radius:var(--r);overflow:hidden}
.list a{display:grid;grid-template-columns:6rem 1fr;gap:2px 10px;padding:12px 16px;border-top:1px solid var(--ln);color:inherit;text-decoration:none}
.list a:first-child{border-top:0}.list a:hover{background:var(--acs)}
.list .d{color:var(--mu);font-size:.82rem}.list .t{color:var(--mu);font-size:.85rem;grid-column:2}
article,.card{background:var(--s);border:1px solid var(--ln);border-radius:var(--r);padding:20px 18px;margin-top:14px}
article h2{font-size:1.4rem;line-height:1.45;margin:0 0 4px}
article h3{font-size:1.12rem;margin:26px 0 8px;padding:6px 0 0 12px;border-left:5px solid #f3b79a}
article h4{font-size:1rem;margin:18px 0 4px;color:var(--gr2)}
.theme{color:var(--mu);margin:0 0 12px}
.concl{background:var(--acs);border-radius:12px;padding:12px 16px;margin:14px 0}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(7rem,1fr));gap:8px;margin:14px 0}
.stats div{background:var(--gr);border-radius:12px;padding:8px 12px}
.stats dt{font-size:.72rem;color:var(--gr2);margin:0}.stats dd{margin:0;font-weight:700}
.scroll{overflow-x:auto;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:.88rem}
th,td{border-bottom:1px solid var(--ln);padding:6px 8px;text-align:left;vertical-align:top}
th{color:var(--gr2);white-space:nowrap;background:#f7fbf9}
.note,.src,.disc{font-size:.82rem;color:var(--mu)}
.src a,footer a{color:var(--ac);overflow-wrap:anywhere}
.disc{border-top:1px solid var(--ln);padding-top:12px;margin-top:18px}
.ad{margin:20px 0;min-height:90px;border:2px dashed var(--ln);border-radius:12px;display:flex;align-items:center;justify-content:center;color:var(--mu);font-size:.75rem}
footer{margin-top:24px;font-size:.8rem;color:var(--mu)}
.flow{margin:14px 0;padding:14px;background:#fffdf9;border:1px solid var(--ln);border-radius:var(--r)}
.flow figcaption{font-weight:700;color:var(--gr2);margin-bottom:10px}
.steps{display:flex;flex-direction:column;align-items:stretch;gap:6px}
.box{background:var(--gr);border-radius:14px;padding:10px 14px;flex:1 1 0;min-width:0}
.box b{display:block;font-size:.95rem}.box span{display:block;font-size:.84rem;color:var(--fg);line-height:1.6}
.arrow{display:flex;align-items:center;justify-content:center;gap:8px;color:var(--ac);font-size:.78rem;line-height:1.4;text-align:center}
.arrow .ar::before{content:"\\2193";font-size:1.4rem}
.arrow em{font-style:normal;max-width:17em}
.fnote{font-size:.82rem;color:var(--mu);margin:10px 0 0}
@media(min-width:680px){.steps{flex-direction:row;align-items:center}.arrow{flex-direction:column;flex:0 0 6.5em}.arrow em{max-width:none}.box:nth-child(3){flex:1.5 1 0}.arrow .ar::before{content:"\\2192"}}
.charts{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:12px;margin:12px 0}
.chart{background:#fffdf9;border:1px solid var(--ln);border-radius:var(--r);padding:10px 12px}
.chart h5{margin:0 0 4px;font-size:.88rem;color:var(--gr2)}
.chart svg{width:100%;height:auto;display:block}
.legend{font-size:.78rem;color:var(--mu);display:flex;gap:12px;flex-wrap:wrap;margin-bottom:2px}
.legend i{display:inline-block;width:.8em;height:.8em;border-radius:3px;margin-right:4px;vertical-align:-1px}
.hbar{display:flex;flex-direction:column;gap:6px;margin-top:6px}
.hbar .row{display:grid;grid-template-columns:10.5em 1fr 3.8em;gap:8px;align-items:center;font-size:.82rem}
.hbar .bar{background:var(--ln);border-radius:99px;height:14px;overflow:hidden}
.hbar .bar i{display:block;height:100%;background:#ef9a78;border-radius:99px}
.hbar .v{text-align:right;font-variant-numeric:tabular-nums}
.chart .cnote{font-size:.74rem;color:var(--mu);margin:4px 0 0}
.q{font-size:1.08rem;font-weight:700;margin:6px 0 14px}
.choices{display:flex;flex-direction:column;gap:10px}
.choice{all:unset;box-sizing:border-box;cursor:pointer;display:flex;gap:12px;align-items:center;background:#fffdf9;border:2px solid var(--ln);border-radius:14px;padding:12px 14px;line-height:1.5}
.choice:hover:not(:disabled){background:var(--acs);border-color:#f3b79a}
.choice:focus-visible{outline:3px solid var(--gr2);outline-offset:2px}
.choice .mk{flex:0 0 2em;height:2em;border-radius:50%;background:var(--acs);color:var(--ac);display:flex;align-items:center;justify-content:center;font-weight:700;font-size:.9rem}
.choice.right{background:var(--gr);border-color:#7db5a3}.choice.right .mk{background:#7db5a3;color:#fff}
.choice.wrong{background:#fdecea;border-color:#e8a29a}.choice.wrong .mk{background:#e8a29a;color:#fff}
.choice:disabled:not(.right):not(.wrong){opacity:.6;cursor:default}
.result{font-weight:700;font-size:1.1rem;margin:14px 0 4px}
.explain{background:var(--gr);border-radius:14px;padding:6px 16px 12px;margin:10px 0}
.explain .calc{background:#fff;border-radius:10px;padding:8px 12px;font-weight:700}
.pager{display:flex;justify-content:space-between;gap:10px;margin-top:16px;flex-wrap:wrap}
.pager a{color:var(--ac);background:var(--s);border:1px solid var(--ln);border-radius:99px;padding:6px 16px;text-decoration:none;font-size:.9rem}
.teaser{display:block;margin-top:14px;padding:14px 18px;background:var(--gr);border-radius:var(--r);color:var(--fg);text-decoration:none}
.teaser b{color:var(--gr2)}
"""

FONT_LINK = ('<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
             '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Zen+Maru+Gothic:wght@400;500;700&display=swap">')


def esc(s):
    return html.escape(str(s))


def decs(vals):
    """グラフ内の小数桁を揃える(0〜2桁)。"""
    for k in (0, 1, 2):
        if all(abs(v - round(v, k)) < 1e-9 for v in vals):
            return k
    return 2


def fmt(v, k=0):
    return f"{v:,.{k}f}"


def page(title, body, depth=0, desc=""):
    pre = "../" * depth
    return ('<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{esc(title)}</title><meta name="description" content="{esc(desc or TAGLINE)}">{FONT_LINK}'
            f'<link rel="stylesheet" href="{pre}style.css"></head><body><div class="wrap">'
            f'<header><h1><a href="{pre}index.html">{SITE}</a></h1><p class="tag">{TAGLINE}</p>'
            f'<nav class="links"><a href="{pre}index.html">新着一覧</a><a href="{pre}quiz/index.html">投資用語クイズ</a>'
            f'<a href="{pre}about.html">このサイトについて・免責</a></nav></header>{body}'
            f'<footer><p>{DISC}</p></footer></div></body></html>')


def flow_html(f):
    parts = []
    for st in f["steps"]:
        if "a" in st:
            parts.append(f'<div class="arrow"><span class="ar" aria-hidden="true"></span><em>{esc(st["a"])}</em></div>')
        else:
            parts.append(f'<div class="box"><b>{esc(st["t"])}</b><span>{esc(st["s"])}</span></div>')
    note = f'<p class="fnote">{esc(f["note"])}</p>' if f.get("note") else ""
    return ('<figure class="flow"><figcaption>儲けの仕組み(図解)</figcaption>'
            f'<div class="steps">{"".join(parts)}</div>{note}</figure>')


def vbar(c):
    labels, series = c["labels"], c["series"]
    n, m = len(labels), len(series)
    W, H, top, bot, side = 360, 210, 26, 34, 8
    allv = [v for s in series for v in s["values"]]
    assert min(allv) >= 0, "負の値のグラフは未対応です"
    mx = max(allv) or 1
    k = decs(allv)
    ph = H - top - bot
    gw = (W - side * 2) / n
    bw = gw * 0.72 / m
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="{esc(c["title"])}の棒グラフ">']
    out.append(f'<line x1="{side}" y1="{H-bot}" x2="{W-side}" y2="{H-bot}" stroke="#f0e2d0" stroke-width="2"/>')
    for i, lab in enumerate(labels):
        gx = side + i * gw + gw * 0.14
        fc = "予想" in lab
        for j, s in enumerate(series):
            v = s["values"][i]
            h = ph * v / mx
            x = gx + j * bw
            y = H - bot - h
            col = COLORS[j % len(COLORS)]
            extra = f' fill-opacity="0.5" stroke="{col}" stroke-dasharray="3 2"' if fc else ""
            out.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw-2:.1f}" height="{max(h,1):.1f}" rx="4" fill="{col}"{extra}/>')
            out.append(f'<text x="{x+(bw-2)/2:.1f}" y="{y-5:.1f}" text-anchor="middle" font-size="10.5" fill="#4a403a">{fmt(v, k)}</text>')
        out.append(f'<text x="{side+i*gw+gw/2:.1f}" y="{H-bot+16}" text-anchor="middle" font-size="10.5" fill="#85776c">{esc(lab)}</text>')
    out.append("</svg>")
    leg = ""
    if m > 1:
        leg = '<div class="legend">' + "".join(f'<span><i style="background:{COLORS[j%len(COLORS)]}"></i>{esc(s["name"])}</span>' for j, s in enumerate(series)) + "</div>"
    cnote = '<p class="cnote">うすい色は会社予想です。</p>' if any("予想" in l for l in labels) else ""
    return f'<div class="chart"><h5>{esc(c["title"])}</h5>{leg}{"".join(out)}{cnote}</div>'


def hbar(c):
    s = c["series"][0]
    mx = max(s["values"]) or 1
    k = decs(s["values"])
    rows = "".join(
        f'<div class="row"><span class="l">{esc(l)}</span><span class="bar"><i style="width:{max(v/mx*100,2):.1f}%"></i></span><span class="v">{fmt(v, k)}</span></div>'
        for l, v in zip(c["labels"], s["values"]))
    unit = f'(単位:{esc(c["unit"])})' if c.get("unit") else ""
    return f'<div class="chart"><h5>{esc(c["title"])}{unit}</h5><div class="hbar">{rows}</div></div>'


def apply_extras(p):
    secs = []
    for s in p["sections"]:
        h = s["html"]
        if p.get("flow") and "<p><b>儲けの仕組み</b></p>" in h:
            h = h.replace("<p><b>儲けの仕組み</b></p>", "<p><b>儲けの仕組み</b></p>" + flow_html(p["flow"]), 1)
        mine = [c for c in p.get("charts", []) if c["section"] == s["title"]]
        by_table = {}
        for c in mine:
            by_table.setdefault(c.get("table", 0), []).append(c)
        marker = "</table></div>"
        pos, start = [], 0
        while True:
            k = h.find(marker, start)
            if k < 0:
                break
            pos.append(k + len(marker))
            start = k + len(marker)
        for t in sorted(by_table, reverse=True):
            assert t < len(pos), f"{p['id']}: {s['title']} に表{t}がありません"
            cs = "".join(hbar(c) if c["type"] == "hbar" else vbar(c) for c in by_table[t])
            h = h[:pos[t]] + f'<div class="charts">{cs}</div>' + h[pos[t]:]
        secs.append((s["title"], h))
    return secs


def post(p):
    st = "".join(f"<div><dt>{k}</dt><dd>{esc(v)}</dd></div>" for k, v in
                 [("株価", f"{p['price']}({p['asOf']})"), ("最低購入代金", p["minBuy"]), ("PER", p["per"]), ("PBR", p["pbr"]), ("配当利回り", p["yield"])])
    secs = ""
    for i, (t, h) in enumerate(apply_extras(p)):
        secs += f"<h3>{esc(t)}</h3>{h}"
        if i == 0:
            secs += AD_SLOT
    src = "".join(f'<li><a href="{esc(x["url"])}" rel="noopener">{esc(x["title"])}</a></li>' for x in p["sources"])
    body = (f'<article><div class="note">{p["date"]} ／ 証券コード {esc(p["code"])}</div><h2>{esc(p["name"])}</h2>'
            f'<p class="theme">{esc(p["theme"])}</p><dl class="stats">{st}</dl><p class="concl">{p["conclusion"]}</p>{secs}'
            f'{AD_SLOT}<h3>参考にした資料</h3><ul class="src">{src}</ul><p class="disc">{DISC}</p></article>')
    return page(f"{p['name']}({p['code']}) | {SITE}", body, 1, p["theme"])


QUIZ_JS = """<script>(function(){
var box=document.getElementById('quiz'),ans=+box.dataset.answer,txt=box.dataset.text;
var btns=box.querySelectorAll('.choice'),res=document.getElementById('result'),ex=document.getElementById('explain'),done=false;
btns.forEach(function(b,i){b.addEventListener('click',function(){
if(done)return;done=true;
btns.forEach(function(x,j){x.disabled=true;if(j===ans)x.classList.add('right');else if(j===i)x.classList.add('wrong');});
res.textContent=(i===ans)?'正解です!':'おしい! 正解は「'+txt+'」です。';
ex.hidden=false;ex.scrollIntoView({behavior:'smooth',block:'nearest'});
});});
})();</script>"""

MARKS = "アイウエ"


def quiz_page(qz, prev, nxt, total):
    n = int(qz["id"][1:])
    ch = "".join(f'<button type="button" class="choice"><span class="mk">{MARKS[i]}</span><span>{esc(c)}</span></button>' for i, c in enumerate(qz["choices"]))
    memo = f'<h4>初心者向けメモ</h4><p>{esc(qz["memo"])}</p>'
    tip = f'<h4>見るときのポイント</h4><p>{esc(qz["tip"])}</p>' if qz.get("tip") else ""
    pager = '<div class="pager">'
    pager += f'<a href="{prev["id"]}.html">← 前の問題</a>' if prev else '<span></span>'
    pager += '<a href="index.html">問題一覧</a>'
    pager += f'<a href="{nxt["id"]}.html">次の問題 →</a>' if nxt else '<span></span>'
    pager += "</div>"
    body = (f'<article><div class="note">投資用語クイズ 第{n}問(全{total}問) ／ 用語:{esc(qz["term"])}</div>'
            f'<h2>{esc(qz["term"])}クイズ</h2><p class="q">{esc(qz["question"])}</p>'
            f'<div id="quiz" data-answer="{qz["answer"]}" data-text="{esc(qz["choices"][qz["answer"]])}"><div class="choices">{ch}</div>'
            '<p id="result" class="result" role="status" aria-live="polite"></p>'
            f'<div id="explain" class="explain" hidden><h4>解説</h4><p class="calc">{esc(qz["calc"])}</p>{memo}{tip}</div></div>'
            '<noscript><style>#explain[hidden]{display:block}</style></noscript>'
            f'{AD_SLOT}{pager}<p class="disc">{QUIZ_DISC}</p></article>{QUIZ_JS}')
    return page(f"{qz['term']}クイズ 第{n}問 | {SITE}", body, 1, f"{qz['term']}の選択式クイズ。回答後に初心者向けの解説が表示されます。")


def main():
    picks = json.load(open(os.path.join(ROOT, "data", "picks.json"), encoding="utf8"))
    quizzes = json.load(open(os.path.join(ROOT, "data", "quizzes.json"), encoding="utf8"))
    blob = json.dumps(picks, ensure_ascii=False) + json.dumps(quizzes, ensure_ascii=False)
    assert NG not in blob, "非公開の評価内容が混ざっています"
    for d in ("posts", "quiz"):
        os.makedirs(os.path.join(OUT, d), exist_ok=True)
        for f in os.listdir(os.path.join(OUT, d)):
            os.remove(os.path.join(OUT, d, f))
    rows = ""
    for p in picks:
        open(os.path.join(OUT, "posts", p["id"] + ".html"), "w", encoding="utf8").write(post(p))
        rows += (f'<a href="posts/{p["id"]}.html"><span class="d">{p["date"]}</span>'
                 f'<span><b>{esc(p["name"])}</b>({esc(p["code"])})</span><span class="t">{esc(p["theme"])}</span></a>')
    teaser = (f'<a class="teaser" href="quiz/index.html"><b>投資用語クイズ(全{len(quizzes)}問)</b><br>'
              'PER・PBR・配当利回りなどを、選択式で楽しく学べます。回答後に初心者向けの解説つき。</a>')
    idx = f'{teaser}<p class="note" style="margin-top:14px">記事は全{len(picks)}件。新しい順です。</p><nav class="list">{rows}</nav>{AD_SLOT}'
    open(os.path.join(OUT, "index.html"), "w", encoding="utf8").write(page(SITE, idx))
    qrows = "".join(f'<a href="{q["id"]}.html"><span class="d">第{int(q["id"][1:])}問</span><span><b>{esc(q["term"])}</b></span>'
                    f'<span class="t">{esc(q["question"])}</span></a>' for q in quizzes)
    qbody = (f'<article><h2>投資用語クイズ</h2><p>投資指標の用語を、選択式のクイズで学べます。1問ごとに1ページで、回答すると初心者向けの解説が出ます。</p>'
             f'<nav class="list">{qrows}</nav>{AD_SLOT}<p class="disc">{QUIZ_DISC}</p></article>')
    open(os.path.join(OUT, "quiz", "index.html"), "w", encoding="utf8").write(page("投資用語クイズ | " + SITE, qbody, 1))
    for i, q in enumerate(quizzes):
        prev = quizzes[i - 1] if i > 0 else None
        nxt = quizzes[i + 1] if i + 1 < len(quizzes) else None
        open(os.path.join(OUT, "quiz", q["id"] + ".html"), "w", encoding="utf8").write(quiz_page(q, prev, nxt, len(quizzes)))
    about = (f"<article><h2>このサイトについて</h2><p>今は目立たないが、今後重要性が増しそうな日本の上場企業を、事業内容を中心にまとめた個人の調査メモです。"
             f"株価指標や用語の簡単な解説、投資用語のクイズもあります。</p><h3>免責事項</h3><p>{DISC}</p>"
             f"<p>情報の出典は各記事の末尾に記載しています。確認できなかった項目は「未確認」と書き、推測では埋めないようにしています。</p>"
             f"<h3>広告について</h3><p>当サイトは広告を掲載することがあります。広告の内容と記事の評価は無関係です。</p></article>")
    open(os.path.join(OUT, "about.html"), "w", encoding="utf8").write(page("このサイトについて | " + SITE, about))
    open(os.path.join(OUT, "style.css"), "w", encoding="utf8").write(CSS)
    open(os.path.join(OUT, ".nojekyll"), "w").close()
    print("built", len(picks), "posts,", len(quizzes), "quizzes")


if __name__ == "__main__":
    main()
