"""
Finance Tracker Bot — handlers.py
Conversation states and all command/callback handlers.
"""

import os
from datetime import datetime
from typing import Optional

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
)
from telegram.ext import (
    ContextTypes, ConversationHandler,
    CommandHandler, MessageHandler, CallbackQueryHandler,
    filters,
)

import storage
import analytics
from models import EXPENSE_CATEGORIES, INCOME_CATEGORIES

# ── Conversation states ───────────────────────────────────────────────────────
(
    TX_TYPE, TX_AMOUNT, TX_CATEGORY, TX_NOTE, TX_DATE,
    BUDGET_CATEGORY, BUDGET_AMOUNT, BUDGET_MONTH,
) = range(8)


# ── Helpers ───────────────────────────────────────────────────────────────────

def current_month() -> str:
    return datetime.now().strftime("%Y-%m")


def fmt_amount(amount: float) -> str:
    return f"{amount:,.0f}".replace(",", " ")


def _kb(buttons: list, cols: int = 2) -> ReplyKeyboardMarkup:
    rows = [buttons[i:i + cols] for i in range(0, len(buttons), cols)]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=True)


def _inline(rows: list) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(rows)


# ── /start ────────────────────────────────────────────────────────────────────

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "👋 *Finance Tracker*\n\n"
        "Команды:\n"
        "➕ /add — добавить транзакцию\n"
        "📊 /stats — статистика за месяц\n"
        "📈 /charts — графики\n"
        "🎯 /budget — управление бюджетами\n"
        "📋 /history — последние 10 записей\n"
        "🗑 /delete — удалить запись\n"
        "❓ /help — помощь\n"
    )
    await update.message.reply_text(text, parse_mode="Markdown")


async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await cmd_start(update, ctx)


# ── ADD TRANSACTION ───────────────────────────────────────────────────────────

async def cmd_add(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = _kb(["💰 Доход", "💸 Расход"])
    await update.message.reply_text(
        "Что добавляем?", reply_markup=kb
    )
    return TX_TYPE


async def tx_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "Доход" in text:
        ctx.user_data["tx_type"] = "income"
    elif "Расход" in text:
        ctx.user_data["tx_type"] = "expense"
    else:
        await update.message.reply_text("Выбери из кнопок 👇")
        return TX_TYPE

    await update.message.reply_text(
        "Введи сумму:", reply_markup=ReplyKeyboardRemove()
    )
    return TX_AMOUNT


async def tx_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи корректную сумму (например: 1500)")
        return TX_AMOUNT

    ctx.user_data["tx_amount"] = amount
    cats = (INCOME_CATEGORIES if ctx.user_data["tx_type"] == "income"
            else EXPENSE_CATEGORIES)
    await update.message.reply_text(
        "Выбери категорию:", reply_markup=_kb(cats, cols=2)
    )
    return TX_CATEGORY


async def tx_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["tx_category"] = update.message.text
    await update.message.reply_text(
        "Комментарий (или /skip):", reply_markup=ReplyKeyboardRemove()
    )
    return TX_NOTE


async def tx_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["tx_note"] = update.message.text
    today = datetime.now().strftime("%Y-%m-%d")
    kb = _kb([today, "Другая дата"])
    await update.message.reply_text(f"Дата? (ГГГГ-ММ-ДД)", reply_markup=kb)
    return TX_DATE


async def tx_note_skip(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["tx_note"] = ""
    today = datetime.now().strftime("%Y-%m-%d")
    kb = _kb([today])
    await update.message.reply_text(f"Дата?", reply_markup=kb)
    return TX_DATE


async def tx_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ Формат: ГГГГ-ММ-ДД (например 2026-06-03)")
        return TX_DATE

    uid = update.effective_user.id
    tx = storage.add_transaction(
        user_id=uid,
        type_=ctx.user_data["tx_type"],
        amount=ctx.user_data["tx_amount"],
        category=ctx.user_data["tx_category"],
        note=ctx.user_data["tx_note"],
        date=text,
    )
    emoji = "💰" if tx.type == "income" else "💸"
    sign = "+" if tx.type == "income" else "-"
    await update.message.reply_text(
        f"{emoji} *Записано!*\n"
        f"ID: `{tx.id}`\n"
        f"Сумма: {sign}{fmt_amount(tx.amount)}\n"
        f"Категория: {tx.category}\n"
        f"Дата: {tx.date}"
        + (f"\nКомментарий: {tx.note}" if tx.note else ""),
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return ConversationHandler.END


# ── STATS ─────────────────────────────────────────────────────────────────────

async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    month = current_month()
    txs = storage.get_transactions(uid, month)
    budgets = storage.get_budgets(uid, month)

    income, expense = analytics.total_by_type(txs)
    balance = income - expense
    sign = "+" if balance >= 0 else ""
    b_emoji = "🟢" if balance >= 0 else "🔴"

    lines = [
        f"📊 *Статистика за {month}*\n",
        f"💰 Доходы:   `{fmt_amount(income)}`",
        f"💸 Расходы:  `{fmt_amount(expense)}`",
        f"{b_emoji} Баланс:   `{sign}{fmt_amount(balance)}`",
    ]

    by_cat = analytics.expenses_by_category(txs)
    if by_cat:
        lines.append("\n*Расходы по категориям:*")
        for cat, val in by_cat.items():
            pct = val / expense * 100 if expense else 0
            lines.append(f"  {cat}:  `{fmt_amount(val)}`  ({pct:.1f}%)")

    bstat = analytics.budget_status(txs, budgets)
    if bstat:
        lines.append("\n*Бюджеты:*")
        for b in bstat:
            icon = "🔴" if b["pct"] >= 90 else "🟡" if b["pct"] >= 70 else "🟢"
            lines.append(
                f"  {icon} {b['category']}:  "
                f"`{fmt_amount(b['spent'])}` / `{fmt_amount(b['budget'])}`  "
                f"({b['pct']}%)"
            )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── CHARTS ────────────────────────────────────────────────────────────────────

async def cmd_charts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = _inline([
        [InlineKeyboardButton("🥧 Расходы по категориям", callback_data="chart_pie")],
        [InlineKeyboardButton("📊 Доходы vs Расходы", callback_data="chart_bar")],
        [InlineKeyboardButton("📈 Динамика баланса", callback_data="chart_line")],
        [InlineKeyboardButton("🎯 Исполнение бюджетов", callback_data="chart_budget")],
    ])
    await update.message.reply_text("Выбери график:", reply_markup=kb)


async def chart_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    uid = query.from_user.id
    month = current_month()
    txs = storage.get_transactions(uid, month)
    budgets = storage.get_budgets(uid, month)

    ctype = query.data
    await query.message.reply_text("⏳ Генерирую график...")

    if ctype == "chart_pie":
        buf = analytics.chart_expenses_pie(txs, month)
    elif ctype == "chart_bar":
        buf = analytics.chart_income_vs_expense(txs, month)
    elif ctype == "chart_line":
        buf = analytics.chart_daily_balance(txs, month)
    elif ctype == "chart_budget":
        bdata = analytics.budget_status(txs, budgets)
        buf = analytics.chart_budget_progress(bdata, month)
    else:
        return

    await query.message.reply_photo(photo=buf)


# ── BUDGET ────────────────────────────────────────────────────────────────────

async def cmd_budget(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Выбери категорию для установки бюджета:",
        reply_markup=_kb(EXPENSE_CATEGORIES, cols=2)
    )
    return BUDGET_CATEGORY


async def budget_category(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["budget_category"] = update.message.text
    await update.message.reply_text(
        f"Бюджет на {current_month()} для *{update.message.text}*?\nВведи сумму:",
        parse_mode="Markdown",
        reply_markup=ReplyKeyboardRemove(),
    )
    return BUDGET_AMOUNT


async def budget_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        amount = float(update.message.text.replace(",", ".").replace(" ", ""))
        if amount <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text("❌ Введи корректную сумму")
        return BUDGET_AMOUNT

    uid = update.effective_user.id
    month = current_month()
    b = storage.set_budget(uid, ctx.user_data["budget_category"], amount, month)
    await update.message.reply_text(
        f"✅ Бюджет установлен!\n"
        f"Категория: {b.category}\n"
        f"Лимит: `{fmt_amount(b.amount)}`\n"
        f"Месяц: {b.month}",
        parse_mode="Markdown",
    )
    return ConversationHandler.END


# ── HISTORY ───────────────────────────────────────────────────────────────────

async def cmd_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    txs = storage.get_transactions(uid)[:10]

    if not txs:
        await update.message.reply_text("История пуста.")
        return

    lines = ["📋 *Последние транзакции:*\n"]
    for t in txs:
        emoji = "💰" if t.type == "income" else "💸"
        sign = "+" if t.type == "income" else "-"
        note = f" — {t.note}" if t.note else ""
        lines.append(
            f"{emoji} `{t.id}` | {t.date} | {t.category}\n"
            f"   {sign}{fmt_amount(t.amount)}{note}"
        )

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── DELETE ────────────────────────────────────────────────────────────────────

async def cmd_delete(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Введи ID записи для удаления (из /history):"
    )


async def handle_delete_id(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # Only triggered by specific /delete flow — handled via context flag
    pass  # See main.py for wiring


# ── CANCEL ────────────────────────────────────────────────────────────────────

async def cmd_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "❌ Отменено.", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


# ── UNKNOWN ───────────────────────────────────────────────────────────────────

async def unknown(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Не понял команду. Введи /help для списка команд."
    )
