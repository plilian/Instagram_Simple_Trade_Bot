import pandas as pd
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.coingecko_api import find_coin_id, fetch_ohlc_history
from services.metrics import calculate_volatility
from config import VOLATILITY_COIN, VOLATILITY_TIMEFRAME

async def volatility_command(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # اگر این تابع از طریق callback_query صدا زده شد پاسخ بده (برای دکمه‌های inline)
    if update.callback_query:
        await update.callback_query.answer()
        chat_id = update.callback_query.message.chat_id
    else:
        chat_id = update.effective_chat.id

    await context.bot.send_message(
        chat_id=chat_id,
        text="📌 لطفا نام یا نماد کوین مورد نظر خود را برای محاسبه نوسان وارد کنید:"
    )
    return VOLATILITY_COIN

async def get_volatility_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):

    coin_query = update.message.text.strip()
    coin_id = find_coin_id(coin_query)

    if not coin_id:
        await update.message.reply_text(
            "⚠️ کوین مورد نظر پیدا نشد. لطفا نام یا نماد معتبر وارد کنید."
        )
        return VOLATILITY_COIN

    context.user_data['coin_id'] = coin_id

    keyboard = [
        [
            InlineKeyboardButton("1 روز (30 دقیقه)", callback_data="volatility_days_1"),
            InlineKeyboardButton("7 روز (4 ساعت)", callback_data="volatility_days_7"),
        ],
        [
            InlineKeyboardButton("14 روز (4 ساعت)", callback_data="volatility_days_14"),
            InlineKeyboardButton("30 روز (4 ساعت)", callback_data="volatility_days_30"),
        ],
        [
            InlineKeyboardButton("90 روز (4 روز)", callback_data="volatility_days_90"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✅ کوین **{coin_id}** انتخاب شد.\n"
        f"لطفا بازه زمانی مورد نظر را انتخاب کنید:\n"
        f"**توجه:** دقت داده‌ها بر اساس بازه زمانی متفاوت است.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return VOLATILITY_TIMEFRAME

async def get_volatility_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    days = int(query.data.split('_')[-1])
    coin_id = context.user_data.get('coin_id')

    df = fetch_ohlc_history(coin_id, days)
    if df.empty:
        await query.edit_message_text(
            "❌ داده‌ای برای این کوین یافت نشد. لطفا دوباره امتحان کنید."
        )
        return ConversationHandler.END

    volatility = calculate_volatility(df)
    if volatility is None:
        await query.edit_message_text(
            "⚠️ محاسبه نوسان قیمت امکان‌پذیر نبود."
        )
        return ConversationHandler.END

    await query.edit_message_text(
        f"📈 نوسان سالانه تخمینی برای **{coin_id}** در {days} روز گذشته:\n"
        f"🔹 **{volatility:.2f}%**"
    )
    return ConversationHandler.END
