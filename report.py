import argparse, json, statistics as st
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Patch

E = ["linkup_fast", "perplexity", "exa_fast"]
NAME = {"linkup_fast": "Linkup fast", "perplexity": "Perplexity Search", "exa_fast": "Exa fast"}
COL = {"linkup_fast": "#2a78d6", "perplexity": "#eb6834", "exa_fast": "#1baf7a"}
INK, INK2, MUTED, GRID, BASE, SURF = "#0b0b0b", "#52514e", "#898781", "#e1e0d9", "#c3c2b7", "#fcfcfb"


def load(path):
    rows = []
    for g in map(json.loads, open(path)):
        if not all(e in g["scores"] for e in E): continue
        s = {e: g["scores"][e]["overall"] for e in E}
        rows.append({**g, **s, "margin": s["linkup_fast"] - max(s["perplexity"], s["exa_fast"]),
                     "rank": 1 + sum(s[e] > s["linkup_fast"] for e in E[1:])})
    return rows


def summary(rows):
    n = len(rows); win = sum(r["margin"] > 0 for r in rows); tie = sum(r["margin"] == 0 for r in rows); loss = sum(r["margin"] < 0 for r in rows)
    print(f"queries graded: {n}  (judge: {rows[0]['judge_model']})")
    print("average overall score (0-10):")
    for e in E:
        sub = {k: round(st.mean(r["scores"][e][k] for r in rows), 2) for k in ("relevance", "completeness", "accuracy")}
        print(f"  {NAME[e]:18} {st.mean(r[e] for r in rows):.2f}   {sub}")
    print(f"Linkup fast vs best competitor: wins {win} ({win/n:.0%}), ties {tie} ({tie/n:.0%}), losses {loss} ({loss/n:.0%}); ranked #1 on {sum(r['rank']==1 for r in rows)}")
    return n, win, tie, loss


def chart(rows, n, win, tie, loss, out):
    avg = {e: st.mean(r[e] for r in rows) for e in E}
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": BASE, "axes.labelcolor": INK2, "xtick.color": MUTED, "ytick.color": INK2})
    fig = plt.figure(figsize=(13, 11), facecolor=SURF)
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1.25], width_ratios=[1, 1.35], hspace=0.42, wspace=0.28)
    fig.text(0.06, 0.965, f"Linkup fast vs Perplexity Search vs Exa fast — {n} queries", fontsize=16, weight="bold", color=INK)
    fig.text(0.06, 0.94, f"Blind side-by-side LLM judge ({rows[0]['judge_model']}) on Samsung's criteria · Linkup ranked #1 on {sum(r['rank']==1 for r in rows)} of {n}", fontsize=10.5, color=INK2)
    ax = fig.add_subplot(gs[0, 0]); ax.set_facecolor(SURF); order = sorted(E, key=lambda e: avg[e])
    ax.barh([NAME[e] for e in order], [avg[e] for e in order], color=[COL[e] for e in order], height=0.5)
    for k, e in enumerate(order): ax.text(avg[e] + 0.12, k, f"{avg[e]:.1f}", va="center", color=INK, weight="bold")
    ax.set_xlim(0, 10); ax.set_title("Average score (0–10)", loc="left", color=INK, weight="bold", fontsize=12)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.tick_params(axis="y", length=0)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax = fig.add_subplot(gs[0, 1]); ax.set_facecolor(SURF)
    cats = [("Linkup scored higher", win, COL["linkup_fast"], "white"), ("Tie for top score", tie, BASE, INK), ("A competitor scored higher", loss, MUTED, "white")]
    left = 0
    for lab, v, c, tc in cats:
        if v:
            ax.barh([0], [v], left=left, color=c, height=0.45, edgecolor=SURF, linewidth=3)
            ax.text(left + v / 2, 0, str(v), ha="center", va="center", color=tc, weight="bold", fontsize=13)
            ax.text(left + v / 2, -0.42, f"{v/n:.0%}", ha="center", va="center", color=INK2, fontsize=10)
        left += v
    ax.set_xlim(0, n); ax.set_ylim(-1.3, 0.5); ax.axis("off")
    ax.set_title(f"Outcome per query (n={n})", loc="left", color=INK, weight="bold", fontsize=12)
    ax.legend(handles=[Patch(color=c, label=l) for l, v, c, tc in cats], loc="lower left", frameon=False, fontsize=9.5, labelcolor=INK2)
    ax = fig.add_subplot(gs[1, 0]); ax.set_facecolor(SURF); srt = sorted(rows, key=lambda r: -r["margin"])
    ax.bar(range(n), [r["margin"] for r in srt], color=[COL["linkup_fast"] if r["margin"] > 0 else MUTED for r in srt], width=0.8, edgecolor=SURF, linewidth=0.5)
    ax.axhline(0, color=BASE, lw=1); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True); ax.set_xticks([])
    for sp in ("top", "right", "bottom"): ax.spines[sp].set_visible(False)
    ax.set_ylabel("Linkup fast minus best competitor (points)")
    ax.set_title("Every query, ranked by Linkup's margin", loc="left", color=INK, weight="bold", fontsize=12)
    ax = fig.add_subplot(gs[1, 1]); ax.set_facecolor(SURF)
    doms = sorted({r["domain"] for r in rows}, key=lambda d: st.mean(r["margin"] for r in rows if r["domain"] == d))
    for k, d in enumerate(doms):
        sub = [r for r in rows if r["domain"] == d]; vals = {e: st.mean(r[e] for r in sub) for e in E}
        ax.plot([min(vals.values()), max(vals.values())], [k, k], color=GRID, lw=2, zorder=1)
        for e in E: ax.scatter(vals[e], k, s=70, color=COL[e], edgecolor=SURF, linewidth=2, zorder=3)
        ax.text(10.15, k, f"n={len(sub)}", va="center", color=MUTED, fontsize=8.5)
    ax.set_yticks(range(len(doms))); ax.set_yticklabels(doms); ax.set_xlim(2, 10); ax.tick_params(axis="y", length=0)
    ax.grid(axis="x", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ("top", "right", "left"): ax.spines[sp].set_visible(False)
    ax.set_title("Average score by vertical", loc="left", color=INK, weight="bold", fontsize=12)
    for e in E: ax.scatter([], [], s=60, color=COL[e], label=NAME[e])
    ax.legend(loc="lower left", bbox_to_anchor=(0, -0.2), ncol=3, frameon=False, fontsize=9, labelcolor=INK2)
    fig.savefig(out, dpi=160, facecolor=SURF, bbox_inches="tight"); print("chart ->", out)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("grades"); ap.add_argument("--chart"); a = ap.parse_args()
    rows = load(a.grades); stats = summary(rows)
    if a.chart: chart(rows, *stats, a.chart)
