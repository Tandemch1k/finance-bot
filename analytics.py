import io
from collections import defaultdict
from datetime import datetime
from typing import List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

from models import Transaction, Budget


# ── Aggregations ──────────────────────────────────────────────────────────────

def total_by_type(txs: List[Transaction]) -> Tuple[float, float]:
    """Returns (total_income, total_expense)."""
    income = sum(t.amount for t in txs if t.type == "income")
    expense = sum(t.amount for t in txs if t.type == "expense")
    return income, expense


def expenses_by_category(txs: List[Transaction]) -> dict:
    result = defaultdict(float)
    for t in txs:
        if t.type == "expense":
            result[t.category] += t.amount
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def income_by_category(txs: List[Transaction]) -> dict:
    result = defaultdict(float)
    for t in txs:
        if t.type == "income":
            result[t.category] += t.amount
    return dict(sorted(result.items(), key=lambda x: x[1], reverse=True))


def daily_balance(txs: List[Transaction]) -> dict:
    """Cumulative balance by day."""
    daily = defaultdict(float)
    for t in txs:
        if t.type == "income":
            daily[t.date] += t.amount
        else:
            daily[t.date] -= t.amount
    dates = sorted(daily.keys())
    cumulative = {}
    balance = 0.0
    for d in dates:
        balance += daily[d]
        cumulative[d] = round(balance, 2)
    return cumulative


def budget_status(txs: List[Transaction],
                  budgets: List[Budget]) -> List[dict]:
    spent = expenses_by_category(txs)
    result = []
    for b in budgets:
        s = spent.get(b.category, 0.0)
        result.append({
            "category": b.category,
            "budget": b.amount,
            "spent": s,
            "left": b.amount - s,
            "pct": round(s / b.amount * 100, 1) if b.amount else 0,
        })
    return sorted(result, key=lambda x: x["pct"], reverse=True)


# ── Charts ────────────────────────────────────────────────────────────────────

COLORS = [
    "#4E79A7", "#F28E2B", "#E15759", "#76B7B2",
    "#59A14F", "#EDC948", "#B07AA1", "#FF9DA7",
    "#9C755F", "#BAB0AC", "#D4A5A5", "#8CD17D",
]

STYLE = {
    "figure.facecolor": "#1a1a2e",
    "axes.facecolor": "#16213e",
    "axes.labelcolor": "#e0e0e0",
    "text.color": "#e0e0e0",
    "xtick.color": "#a0a0a0",
    "ytick.color": "#a0a0a0",
    "grid.color": "#2a2a4a",
    "grid.linestyle": "--",
    "grid.alpha": 0.5,
}


def _apply_style():
    for k, v in STYLE.items():
        plt.rcParams[k] = v


def chart_expenses_pie(txs: List[Transaction], month: str) -> io.BytesIO:
    _apply_style()
    by_cat = expenses_by_category(txs)
    if not by_cat:
        return _empty_chart("Нет расходов за период")

    labels = list(by_cat.keys())
    values = list(by_cat.values())
    colors = COLORS[:len(labels)]

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor("#1a1a2e")

    wedges, texts, autotexts = ax.pie(
        values,
        labels=None,
        colors=colors,
        autopct="%1.1f%%",
        startangle=140,
        pctdistance=0.75,
        wedgeprops={"linewidth": 1.5, "edgecolor": "#1a1a2e"},
    )
    for at in autotexts:
        at.set_color("white")
        at.set_fontsize(9)

    # Legend with amounts
    legend_labels = [f"{l}  —  {v:,.0f}" for l, v in zip(labels, values)]
    ax.legend(wedges, legend_labels, loc="lower center",
              bbox_to_anchor=(0.5, -0.15), ncol=2,
              fontsize=8, framealpha=0.2, labelcolor="#e0e0e0")

    ax.set_title(f"Расходы по категориям\n{month}", color="#e0e0e0",
                 fontsize=13, pad=15)
    plt.tight_layout()
    return _fig_to_bytes(fig)


def chart_income_vs_expense(txs: List[Transaction], month: str) -> io.BytesIO:
    _apply_style()
    income, expense = total_by_type(txs)

    fig, ax = plt.subplots(figsize=(7, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    bars = ax.bar(["Доходы", "Расходы"], [income, expense],
                  color=["#59A14F", "#E15759"], width=0.5,
                  edgecolor="#1a1a2e", linewidth=1.5)

    for bar, val in zip(bars, [income, expense]):
        ax.text(bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(income, expense) * 0.02,
                f"{val:,.0f}", ha="center", va="bottom",
                color="white", fontsize=11, fontweight="bold")

    ax.set_title(f"Доходы vs Расходы  |  {month}",
                 color="#e0e0e0", fontsize=13, pad=12)
    ax.set_ylabel("Сумма", color="#a0a0a0")
    ax.yaxis.grid(True)
    ax.set_axisbelow(True)

    balance = income - expense
    color = "#59A14F" if balance >= 0 else "#E15759"
    sign = "+" if balance >= 0 else ""
    ax.set_xlabel(f"Баланс: {sign}{balance:,.0f}", color=color,
                  fontsize=11, labelpad=10)

    plt.tight_layout()
    return _fig_to_bytes(fig)


def chart_daily_balance(txs: List[Transaction], month: str) -> io.BytesIO:
    _apply_style()
    data = daily_balance(txs)
    if not data:
        return _empty_chart("Нет данных за период")

    dates = list(data.keys())
    values = list(data.values())
    x = list(range(len(dates)))

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    color = "#59A14F" if values[-1] >= 0 else "#E15759"
    ax.plot(x, values, color=color, linewidth=2, marker="o",
            markersize=4, markerfacecolor="white")
    ax.fill_between(x, values, alpha=0.15, color=color)
    ax.axhline(0, color="#a0a0a0", linewidth=0.8, linestyle="--")

    step = max(1, len(dates) // 8)
    ax.set_xticks(x[::step])
    ax.set_xticklabels([d[5:] for d in dates[::step]],
                       rotation=30, ha="right", fontsize=8)

    ax.yaxis.grid(True)
    ax.set_axisbelow(True)
    ax.set_title(f"Динамика баланса  |  {month}",
                 color="#e0e0e0", fontsize=13, pad=12)
    ax.set_ylabel("Баланс", color="#a0a0a0")

    plt.tight_layout()
    return _fig_to_bytes(fig)


def chart_budget_progress(budget_data: List[dict], month: str) -> io.BytesIO:
    _apply_style()
    if not budget_data:
        return _empty_chart("Бюджеты не установлены")

    fig, ax = plt.subplots(figsize=(8, max(4, len(budget_data) * 0.9)))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")

    categories = [d["category"] for d in budget_data]
    pcts = [min(d["pct"], 100) for d in budget_data]
    colors = ["#E15759" if p >= 90 else "#F28E2B" if p >= 70
              else "#59A14F" for p in pcts]

    y = list(range(len(categories)))
    ax.barh(y, pcts, color=colors, edgecolor="#1a1a2e",
            linewidth=1, height=0.6)
    ax.barh(y, [100] * len(y), color="#2a2a4a",
            edgecolor="#1a1a2e", linewidth=1, height=0.6)
    ax.barh(y, pcts, color=colors, edgecolor="#1a1a2e",
            linewidth=1, height=0.6)

    for i, d in enumerate(budget_data):
        left_str = (f"осталось {d['left']:,.0f}" if d["left"] >= 0
                    else f"перерасход {abs(d['left']):,.0f}")
        ax.text(102, i, f"{d['pct']}%  ({left_str})",
                va="center", color="#e0e0e0", fontsize=8)

    ax.set_yticks(y)
    ax.set_yticklabels(categories, fontsize=9)
    ax.set_xlim(0, 170)
    ax.set_xlabel("% использования бюджета", color="#a0a0a0")
    ax.axvline(100, color="#a0a0a0", linewidth=1, linestyle="--", alpha=0.5)
    ax.set_title(f"Исполнение бюджетов  |  {month}",
                 color="#e0e0e0", fontsize=13, pad=12)
    ax.xaxis.grid(True)
    ax.set_axisbelow(True)

    plt.tight_layout()
    return _fig_to_bytes(fig)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fig_to_bytes(fig) -> io.BytesIO:
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


def _empty_chart(message: str) -> io.BytesIO:
    _apply_style()
    fig, ax = plt.subplots(figsize=(6, 3))
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#16213e")
    ax.text(0.5, 0.5, message, ha="center", va="center",
            color="#a0a0a0", fontsize=14, transform=ax.transAxes)
    ax.axis("off")
    return _fig_to_bytes(fig)
