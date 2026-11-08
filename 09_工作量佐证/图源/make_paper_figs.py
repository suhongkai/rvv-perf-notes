# -*- coding: utf-8 -*-
"""生成技术报告的学术风格图（matplotlib，300 dpi）。

输出：11_提交_2026-11-08/02_技术报告/figs/fig{1..5}_*.png
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUT = r"F:\1\RISC-V工业监控_新赛事规划\11_提交_2026-11-08\02_技术报告\figs"
os.makedirs(OUT, exist_ok=True)

plt.rcParams.update({
    "font.family": ["Times New Roman", "SimSun"],
    "font.size": 8.5,
    "axes.linewidth": 0.8,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "xtick.direction": "out",
    "ytick.direction": "out",
    "xtick.major.width": 0.8,
    "ytick.major.width": 0.8,
    "legend.frameon": False,
    "figure.dpi": 300,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.grid": True,
    "grid.linestyle": ":",
    "grid.linewidth": 0.5,
    "grid.color": "#c8c8c8",
})

C_STOCK = "#9a9a9a"
C_NEW = "#7fa8c9"
C_MEE = "#c98a3c"
C_OURS = "#2f5d8a"
C_2B = "#2f5d8a"
C_4B = "#b03a2e"


def save(fig, name):
    p = os.path.join(OUT, name)
    fig.savefig(p, dpi=300)
    plt.close(fig)
    print("saved", name)


# ---------------- 图 1：同板四臂 ----------------
def fig1():
    models = [("2B", [5.05, 5.02, 19.16, 19.38], [2.798, 2.856, 2.809, 3.987]),
              ("4B", [1.951, 1.958, 7.639, 7.717], [1.254, 1.183, 1.170, 1.706])]
    arms = ["stock", "官方新后端", "官方 MEE", "chunk16"]
    colors = [C_STOCK, C_NEW, C_MEE, C_OURS]
    fig, axes = plt.subplots(2, 2, figsize=(6.9, 4.6))
    for r, (m, pref, dec) in enumerate(models):
        for c, vals in enumerate((pref, dec)):
            ax = axes[r][c]
            x = np.arange(4)
            bars = ax.bar(x, vals, width=0.62, color=colors, edgecolor="black", linewidth=0.5)
            for b, v in zip(bars, vals):
                ax.text(b.get_x() + b.get_width() / 2, v + max(vals) * 0.02, f"{v:.2f}" if v < 10 else f"{v:.1f}",
                        ha="center", va="bottom", fontsize=7.2)
            ax.set_xticks(x, arms, fontsize=7.6, rotation=12)
            ax.set_ylim(0, max(vals) * 1.22)
            ax.set_ylabel("t/s", fontsize=8.5)
            ax.grid(axis="x", visible=False)
            if r == 0:
                ax.set_title("预填" if c == 0 else "生成", fontsize=9, pad=6)
            if c == 0:
                ax.text(-0.30, 0.5, m, transform=ax.transAxes, rotation=90, va="center",
                        ha="center", fontsize=10, fontweight="bold")
    fig.tight_layout(pad=0.6)
    save(fig, "fig1_four_arm.png")


# ---------------- 图 2：首 token 时延 ----------------
def fig2():
    lengths = [128, 512, 1024]
    data = {
        "2B": dict(stock=[7.0966, 33.3843, 67.0221], ours=[5.0473, 19.4892, 40.1514],
                   stock_rng=[(6.9215, 7.1728), (32.9412, 34.3182), (66.7643, 68.2674)],
                   ours_rng=[(5.0155, 5.3703), (19.2532, 19.6570), (39.9771, 40.3221)]),
        "4B": dict(stock=[18.4841, 85.9688, 173.5709], ours=[12.8092, 49.4713, 99.5631],
                   stock_rng=[(18.3036, 18.8131), (85.2740, 86.0486), (172.8629, 174.3343)],
                   ours_rng=[(12.2883, 12.8901), (49.0397, 49.5299), (99.0864, 100.8493)]),
    }
    fig, axes = plt.subplots(1, 2, figsize=(6.9, 2.9))
    for ax, m in zip(axes, ("2B", "4B")):
        d = data[m]
        x = np.arange(3)
        for series, color, marker, label in (("stock", C_STOCK, "s", "stock"),
                                             ("ours", C_OURS, "o", "chunk16")):
            vals = d[series]
            lo = [v - r[0] for v, r in zip(vals, d[series + "_rng"])]
            hi = [r[1] - v for v, r in zip(vals, d[series + "_rng"])]
            ax.errorbar(x, vals, yerr=[lo, hi], color=color, marker=marker, ms=4.5,
                        lw=1.2, capsize=3, elinewidth=0.8, label=label)
        ax.set_yscale("log")
        ax.set_yticks([5, 10, 20, 50, 100, 200])
        ax.yaxis.set_major_formatter(matplotlib.ticker.ScalarFormatter())
        ax.yaxis.set_minor_formatter(matplotlib.ticker.NullFormatter())
        ax.set_xticks(x, [str(L) for L in lengths])
        ax.set_xlabel("提示长度 / token", fontsize=8.5)
        ax.set_ylabel("首 token 时延 / s", fontsize=8.5)
        ax.set_title(m, fontsize=9.5)
        ax.set_ylim(4, 260)
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", ncol=2, bbox_to_anchor=(0.5, 1.02), fontsize=8)
    fig.tight_layout(pad=0.5, rect=(0, 0, 1, 0.94))
    save(fig, "fig2_ttft.png")


# ---------------- 图 3：长上下文预填 ----------------
def fig3():
    l2 = [1, 2, 4, 8, 10, 16, 32]
    v2 = [25.365, 23.217, 20.874, 17.814, 16.343, 12.822, 8.400]
    l4 = [1, 2, 4, 8, 10, 16, 32]
    v4 = [10.260, 9.724, 9.000, 8.009, 7.405, 6.480, 4.608]
    fig, ax = plt.subplots(figsize=(5.2, 3.3))
    ax.plot(l2, v2, "-o", color=C_2B, ms=4.5, lw=1.2, label="2B")
    ax.plot(l4, v4, "-s", color=C_4B, ms=4.5, lw=1.2, label="4B")
    ax.set_xscale("log", base=2)
    ax.set_xticks(l2, ["1K", "2K", "4K", "8K", "10K", "16K", "32K"], fontsize=7.8)
    ax.set_xlabel("上下文长度 / token", fontsize=8.5)
    ax.set_ylabel("预填吞吐 / (t/s)", fontsize=8.5)
    ax.set_ylim(0, 28)
    ax.annotate("25.37", (1, 25.365), textcoords="offset points", xytext=(6, 2), fontsize=6.8, color=C_2B)
    ax.annotate("8.40", (32, 8.400), textcoords="offset points", xytext=(6, -2), fontsize=6.8, color=C_2B)
    ax.annotate("10.26", (1, 10.260), textcoords="offset points", xytext=(6, 2), fontsize=6.8, color=C_4B)
    ax.annotate("4.61", (32, 4.608), textcoords="offset points", xytext=(6, -2), fontsize=6.8, color=C_4B)
    ax.legend(loc="upper right", fontsize=8)
    fig.tight_layout(pad=0.4)
    save(fig, "fig3_ctx.png")


# ---------------- 图 4：decode 随深度 ----------------
def fig4():
    depth = [0, 2048, 4096, 8192]
    v = [4.303, 4.286, 4.040, 3.663]
    fig, ax = plt.subplots(figsize=(4.4, 2.9))
    ax.plot(depth, v, "-o", color=C_2B, ms=5, lw=1.2)
    for x, y in zip(depth, v):
        ax.annotate(f"{y:.3f}", (x, y), textcoords="offset points", xytext=(6, 6), fontsize=6.8, color=C_2B)
    ax.set_xlabel("上下文深度 / token", fontsize=8.5)
    ax.set_ylabel("生成吞吐 / (t/s)", fontsize=8.5)
    ax.set_xlim(-400, 9000)
    ax.set_ylim(3.4, 4.6)
    ax.annotate("保留 85.1%", xy=(8192, 3.663), xytext=(5200, 3.55), fontsize=7.2,
                arrowprops=dict(arrowstyle="->", lw=0.7, color="black"))
    fig.tight_layout(pad=0.4)
    save(fig, "fig4_decode_depth.png")


# ---------------- 图 5：2B 预填分解瀑布 ----------------
def fig5():
    labels = ["第三方\n基线", "+ 内核", "+ 自量化", "+ chunk16"]
    vals = [12.174, 14.596, 20.710, 25.100]
    fig, ax = plt.subplots(figsize=(5.2, 3.1))
    x = np.arange(4)
    bottoms = [0, vals[0], vals[1], vals[2]]
    heights = [vals[0], vals[1] - vals[0], vals[2] - vals[1], vals[3] - vals[2]]
    colors = [C_STOCK, C_NEW, C_MEE, C_OURS]
    bars = ax.bar(x, heights, bottom=bottoms, width=0.58, color=colors, edgecolor="black", linewidth=0.5)
    for i, (b, v) in enumerate(zip(bars, vals)):
        ax.text(b.get_x() + b.get_width() / 2, v + 0.6, f"{v:.1f}", ha="center", va="bottom", fontsize=7.6)
    for i, pct in zip((1, 2, 3), ("+19.9%", "+41.9%", "+20.8%")):
        ax.text(i, bottoms[i] + heights[i] / 2, pct, ha="center", va="center", fontsize=7, color="white")
    ax.set_xticks(x, labels, fontsize=7.8)
    ax.set_ylabel("2B 预填吞吐 / (t/s)", fontsize=8.5)
    ax.set_ylim(0, 29)
    ax.grid(axis="x", visible=False)
    fig.tight_layout(pad=0.4)
    save(fig, "fig5_waterfall.png")


if __name__ == "__main__":
    fig1(); fig2(); fig3(); fig4(); fig5()
