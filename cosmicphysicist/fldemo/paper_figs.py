#!/usr/bin/env python3
"""
Generate INDIS 2026 paper figures from measured data.

  Fig 1  architecture block diagram with byte-annotated data paths
  Fig 2  bytes-to-target vs per-client data volume S (the crossover figure)
  Fig 3  validation accuracy vs cumulative WAN bytes (Mode B curves; Mode A
         upload costs as reference lines)

Sources: fldemo/data/modeAB_results.json (Figs 2-3). Output: fldemo/figs/*.{pdf,png}.

Usage:  python -m fldemo.paper_figs
"""

import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(__file__)
DATA = os.path.join(HERE, "data")
OUT = os.path.abspath(os.path.join(HERE, "figs"))

# Validated palette (dataviz reference instance; pair + ordered ramp checked)
BLUE = "#2a78d6"     # Mode B / federated
RED = "#e34948"      # Mode A / centralized
SEQ = ["#4f90da", "#2a63b0", "#16437e"]   # ordered S = 50 / 150 / 450
INK = "#0b0b0b"
INK2 = "#52514e"
GRID = "#d8d6d0"
GRAY = "#9a9891"

plt.rcParams.update({
    "font.family": "serif", "font.size": 8, "axes.titlesize": 8,
    "axes.labelsize": 8, "xtick.labelsize": 7.5, "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5, "axes.edgecolor": INK2, "axes.linewidth": 0.6,
    "xtick.color": INK2, "ytick.color": INK2, "axes.labelcolor": INK,
    "text.color": INK, "figure.dpi": 300, "savefig.dpi": 300,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.4,
    "legend.frameon": False,
})
COL_W = 3.35  # IEEE single-column width, inches


def _save(fig, name):
    os.makedirs(OUT, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(OUT, f"{name}.{ext}"), bbox_inches="tight",
                    facecolor="white")
    plt.close(fig)
    print(f"  wrote {name}.pdf/.png")


def _results():
    return json.load(open(os.path.join(DATA, "modeAB_results.json")))["results"]


def fig2_crossover():
    rows = [r for r in _results() if r["K"] == 10]
    rows.sort(key=lambda r: r["S"])
    S = [r["S"] for r in rows]
    a = [r["modeA"]["upload_bytes"] / 1024 for r in rows]
    b = [r["modeB"]["fl_bytes"] / 1024 for r in rows]

    fig, ax = plt.subplots(figsize=(COL_W, 2.4))
    ax.plot(S, a, "-o", color=RED, lw=1.4, ms=4.5, label="Mode A (centralized)")
    ax.plot(S, b, "--s", color=BLUE, lw=1.4, ms=4.5, label="Mode B (federated)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xticks(S); ax.set_xticklabels([str(s) for s in S])
    ax.set_xlabel("detections held per client, S  (K = 10 clients)")
    ax.set_ylabel("WAN kilobytes to 0.95 accuracy")
    ax.legend(loc="upper left")
    for s, av, bv, r in zip(S, a, b, rows):
        if r["reduction_x"] >= 2:   # label sits in the A–B gap
            ax.annotate(f"{r['reduction_x']:.1f}×", (s, np.sqrt(av * bv)),
                        ha="center", va="center", fontsize=7.5, color=INK2)
        else:                        # gap too small — offset above the points
            ax.annotate(f"{r['reduction_x']:.1f}×", (s, av),
                        xytext=(10, 10), textcoords="offset points",
                        fontsize=7.5, color=INK2)
    ax.set_title("Reduction is set by data volume per client", loc="left")
    _save(fig, "fig2_crossover")


def fig3_acc_vs_bytes():
    rows = [r for r in _results() if r["K"] == 10]
    rows.sort(key=lambda r: r["S"])
    styles = ["-", "--", "-."]

    fig, ax = plt.subplots(figsize=(COL_W, 2.5))
    for row, c, ls in zip(rows, SEQ, styles):
        curve = row["modeB"]["curve"]
        kb = [p["fl_bytes"] / 1024 for p in curve]
        acc = [p["accuracy"] for p in curve]
        ax.plot(kb, acc, ls, color=c, lw=1.3)
        # Mode A upload cost as a labelled reference line
        akb = row["modeA"]["upload_bytes"] / 1024
        ax.axvline(akb, color=RED, lw=0.8, alpha=0.55)
        ax.annotate(f"centralized, S={row['S']}", (akb, 0.37),
                    xytext=(-7, 0), textcoords="offset points", rotation=90,
                    fontsize=6.3, color=RED, ha="center", va="bottom")
    # The three federated curves nearly coincide — that IS the finding.
    ax.annotate("federated, S = 50 / 150 / 450\n(near-identical cost)",
                (150, 0.615), xytext=(9, 0.78), fontsize=7,
                color=SEQ[1],
                arrowprops=dict(arrowstyle="-", color=SEQ[1], lw=0.7))
    ax.axhline(0.95, color=INK2, lw=0.6, ls=":", alpha=0.8)
    ax.annotate("0.95 target", (5.6, 0.958), fontsize=6.5, color=INK2)
    ax.set_xscale("log")
    ax.set_xlim(4, 12000)
    ax.set_ylim(0.35, 1.02)
    ax.set_xlabel("cumulative WAN kilobytes (log)")
    ax.set_ylabel("global validation accuracy")
    ax.set_title("Accuracy per WAN byte, federated (curves) vs\n"
                 "centralized one-time upload (vertical lines)", loc="left")
    _save(fig, "fig3_acc_vs_bytes")



def fig1_architecture():
    """Single-column layout: 2x2 box grid, WAN paths byte-annotated."""
    fig, ax = plt.subplots(figsize=(COL_W, 2.9))
    ax.set_xlim(0, 100); ax.set_ylim(0, 86)
    ax.axis("off"); ax.grid(False)

    def box(x, y, w, h, title, sub, fc="#f2f1ed", ec=INK2):
        ax.add_patch(FancyBboxPatch((x, y), w, h, fc=fc, ec=ec, lw=0.8,
                     boxstyle="round,pad=0.6,rounding_size=1.2"))
        ax.text(x + w / 2, y + h - 4.4, title, ha="center", fontsize=7.4,
                weight="bold", color=INK)
        ax.text(x + w / 2, y + h / 2 - 4.4, sub, ha="center", va="center",
                fontsize=6.2, color=INK2, linespacing=1.35)

    def arrow(x0, y0, x1, y1, color=BLUE, ls="-"):
        ax.annotate("", (x1, y1), (x0, y0),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=1.1,
                                    linestyle=ls, mutation_scale=8))

    box(1, 58, 34, 26, "Phones (N)",
        "PWA detector · cluster\n+ hot-pixel mask ·\nin-browser trainer")
    box(65, 58, 34, 26, "FL coordinator",
        "NRP/Nautilus · FedAvg\n· straggler-tolerant ·\nvalidation, byte ctrs")
    box(65, 24, 34, 22, "Live dashboard",
        "accuracy curve ·\nclient tiles · WAN\nmeters · referee panel")
    box(1, 2, 34, 18, "CosmicWatch",
        "scintillator telescope\n1.84 Hz · 232 h")
    box(65, 2, 34, 14, "Referee harness",
        "reference rate\ncomparison")

    # phones <-> coordinator (WAN)
    arrow(36.5, 78, 63.5, 78, BLUE)
    ax.text(50, 80.4, "weights 0.8 KB", ha="center", va="bottom",
            fontsize=6.0, color=BLUE)
    arrow(63.5, 64, 36.5, 64, BLUE)
    ax.text(50, 61.2, "global model ·\n≈2.1 KB/round", ha="center",
            va="top", fontsize=6.0, color=BLUE, linespacing=1.2)
    ax.text(18, 51.5, "raw pixels never leave the device", ha="center",
            fontsize=6.0, style="italic", color=RED)
    # coordinator -> dashboard
    arrow(82, 56.5, 82, 47.5, INK2)
    ax.text(80, 52, "status JSON", ha="right", fontsize=6.0, color=INK2)
    # referee chain
    arrow(36.5, 9, 63.5, 9, INK2)
    ax.text(50, 11.4, "1.54 M events", ha="center", fontsize=6.0, color=INK2)
    arrow(82, 17, 82, 22.5, INK2)
    ax.text(80, 19.7, "rate comparison", ha="right", fontsize=6.0,
            color=INK2)
    _save(fig, "fig1_architecture")


def fig_protocol():
    """Client-protocol sequence diagram with per-message byte annotations
    (paper Fig: client_protocol). Column width, paper typography."""
    fig, ax = plt.subplots(figsize=(COL_W, 3.0))
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off"); ax.grid(False)

    LANES = [(13, "Phone", "(browser PWA)"),
             (53, "FL coordinator", "(NRP/Nautilus)"),
             (89, "Validation set", "(782 held-out)")]
    for x, t1, t2 in LANES:
        ax.add_patch(FancyBboxPatch((x - 12, 90), 24, 9, fc="#f2f1ed",
                     ec=INK2, lw=0.8,
                     boxstyle="round,pad=0.4,rounding_size=1.0"))
        ax.text(x, 96.2, t1, ha="center", fontsize=6.8, weight="bold",
                color=INK)
        ax.text(x, 92.2, t2, ha="center", fontsize=5.8, color=INK2)
        ax.plot([x, x], [10, 89.6], color=INK2, lw=0.6, ls=(0, (3, 3)),
                zorder=0)

    def msg(y, x0, x1, label, color=BLUE, ls="-", fs=6.0):
        ax.annotate("", (x1, y), (x0, y),
                    arrowprops=dict(arrowstyle="-|>", color=color, lw=0.9,
                                    linestyle=ls, mutation_scale=7))
        ax.text((x0 + x1) / 2, y + 1.4, label, ha="center", fontsize=fs,
                color=color)

    def note(y, x, label, color=INK2):
        ax.plot([x], [y], marker="o", ms=2.4, color=color)
        ax.text(x + 2.5, y, label, ha="left", va="center", fontsize=6.0,
                color=color, style="italic")

    # setup
    msg(85, 13, 53, "register")
    msg(79, 53, 13, "global weights + lr ($\\sim$1.0 KB)", ls="--")
    msg(73, 53, 13, "seed shard (demo bootstrap; excluded)", color=GRAY,
        ls="--")

    # one round, boxed
    ax.add_patch(FancyBboxPatch((3, 12), 94, 53, fc="none", ec=INK2, lw=0.7,
                 boxstyle="round,pad=0.4,rounding_size=1.0"))
    ax.text(5.5, 61.5, "round $r$", fontsize=6.6, color=INK, weight="bold")
    msg(56, 53, 13, "global weights + lr ($\\sim$1.0 KB)", ls="--")
    note(49, 13, "train locally: 1 epoch, 41 params (0 WAN bytes)")
    msg(42, 13, 53, "submit weights 802 B + count ($\\sim$1.1 KB)")
    note(35, 53, "validate (shapes, finite, bounds) $\\cdot$ FedAvg at"
                 " $K_{\\min}$/timeout")
    msg(28, 53, 89, "evaluate global model", color=INK2)
    msg(21, 89, 53, "accuracy $\\to$ public curve", color=INK2, ls="--")

    ax.text(50, 6.5, "rounds repeat to the 0.95 target $\\cdot$"
            " $\\approx$2.1 KB per client per round, total",
            ha="center", fontsize=6.4, color=INK)
    _save(fig, "client_protocol")


if __name__ == "__main__":
    print(f"output -> {OUT}")
    fig1_architecture()
    fig2_crossover()
    fig3_acc_vs_bytes()
    fig_protocol()
