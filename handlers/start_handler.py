from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    keyboard = [
        [
            InlineKeyboardButton("📊 تحلیل RSI", callback_data="rsi"),
            InlineKeyboardButton("📈 نوسانات (Volatility)", callback_data="volatility"),
        ],
        [
            InlineKeyboardButton("⚖️ نسبت ریسک به ریوارد", callback_data="riskreward"),
        ],
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "👋 سلام!\n\n"
        "من ربات تحلیلگر ارز دیجیتال هستم، اینجا می‌تونی به سرعت و راحت به ابزارهای تحلیلی دسترسی داشته باشی.\n\n"
        "کافیه گزینه موردنظرت رو انتخاب کنی:\n\n"
        "🔹 تحلیل RSI: بررسی مناطق اشباع خرید و فروش\n"
        "🔹 نوسانات: تحلیل میزان ریسک بازار\n"
        "🔹 نسبت ریسک به ریوارد: مدیریت هوشمندانه ریسک معاملات\n\n"
        "برای شروع، یکی از دکمه‌ها رو انتخاب کن."
    )

    await update.message.reply_text(
        welcome_text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

    return ConversationHandler.END
