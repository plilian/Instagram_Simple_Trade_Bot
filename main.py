from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from handlers.start_handler import start_command
from handlers.rsi_handler import rsi_command, get_rsi_coin, get_rsi_timeframe
from handlers.volatility_handler import volatility_command, get_volatility_coin, get_volatility_timeframe
from handlers.riskreward_handler import riskreward_command, get_riskreward_entry, get_riskreward_stop, get_riskreward_target
from config import (
    RSI_COIN, RSI_TIMEFRAME,
    VOLATILITY_COIN, VOLATILITY_TIMEFRAME,
    RISKREWARD_ENTRY, RISKREWARD_STOP, RISKREWARD_TARGET
)
import os

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

def main():

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start_command))

    rsi_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(rsi_command, pattern='^rsi$')],
        states={
            RSI_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_rsi_coin)],
            RSI_TIMEFRAME: [CallbackQueryHandler(get_rsi_timeframe, pattern='^rsi_days_')],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    volatility_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(volatility_command, pattern='^volatility$')],
        states={
            VOLATILITY_COIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_volatility_coin)],
            VOLATILITY_TIMEFRAME: [CallbackQueryHandler(get_volatility_timeframe, pattern='^volatility_days_')],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    riskreward_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(riskreward_command, pattern='^riskreward$')],
        states={
            RISKREWARD_ENTRY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_riskreward_entry)],
            RISKREWARD_STOP: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_riskreward_stop)],
            RISKREWARD_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_riskreward_target)],
        },
        fallbacks=[],
        allow_reentry=True,
    )

    app.add_handler(rsi_handler)
    app.add_handler(volatility_handler)
    app.add_handler(riskreward_handler)

    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    main()
