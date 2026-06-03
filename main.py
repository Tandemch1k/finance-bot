"""
Finance Tracker Bot — main.py
Run: python main.py
Requires: BOT_TOKEN env variable
"""

import logging
import os

from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ConversationHandler, filters,
)

from handlers import (
    cmd_start, cmd_help, cmd_add, cmd_stats, cmd_charts,
    cmd_budget, cmd_history, cmd_cancel, chart_callback, unknown,
    tx_type, tx_amount, tx_category, tx_note, tx_note_skip, tx_date,
    budget_category, budget_amount,
    TX_TYPE, TX_AMOUNT, TX_CATEGORY, TX_NOTE, TX_DATE,
    BUDGET_CATEGORY, BUDGET_AMOUNT,
)

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def build_app() -> Application:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise RuntimeError("BOT_TOKEN environment variable not set")

    app = Application.builder().token(token).build()

    # ── Add transaction conversation ──────────────────────────────────────────
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("add", cmd_add)],
        states={
            TX_TYPE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, tx_type)],
            TX_AMOUNT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, tx_amount)],
            TX_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, tx_category)],
            TX_NOTE: [
                CommandHandler("skip", tx_note_skip),
                MessageHandler(filters.TEXT & ~filters.COMMAND, tx_note),
            ],
            TX_DATE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, tx_date)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # ── Set budget conversation ───────────────────────────────────────────────
    budget_conv = ConversationHandler(
        entry_points=[CommandHandler("budget", cmd_budget)],
        states={
            BUDGET_CATEGORY: [MessageHandler(filters.TEXT & ~filters.COMMAND, budget_category)],
            BUDGET_AMOUNT:   [MessageHandler(filters.TEXT & ~filters.COMMAND, budget_amount)],
        },
        fallbacks=[CommandHandler("cancel", cmd_cancel)],
    )

    # ── Register handlers ─────────────────────────────────────────────────────
    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("charts",  cmd_charts))
    app.add_handler(CommandHandler("history", cmd_history))
    app.add_handler(add_conv)
    app.add_handler(budget_conv)
    app.add_handler(CallbackQueryHandler(chart_callback, pattern="^chart_"))
    app.add_handler(MessageHandler(filters.COMMAND, unknown))

    return app


if __name__ == "__main__":
    logger.info("Starting Finance Tracker Bot...")
    app = build_app()
    app.run_polling(drop_pending_updates=True)
