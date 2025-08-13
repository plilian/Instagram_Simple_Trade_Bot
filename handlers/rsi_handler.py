import asyncio
import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.coingecko_api import find_coin_id, fetch_ohlc_history
from services.metrics import calculate_rsi
from utils.helpers import format_number
from config import RSI_COIN, RSI_TIMEFRAME


def generate_rsi_chart(df: pd.DataFrame, rsi_values: pd.Series, coin_id: str, days: int):
    plt.style.use('dark_background')
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10), gridspec_kw={'height_ratios': [3, 1]})

    if not pd.api.types.is_datetime64_any_dtype(df['timestamp']):
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')

    ax1.plot(df['timestamp'], df['close'], label=f'{coin_id.capitalize()} Price', color='white')
    ax1.set_title(f'Price and RSI for {coin_id.capitalize()} over {days} days', color='white', fontsize=16)
    ax1.set_ylabel('Price (USD)', color='white')
    ax1.grid(True, linestyle='--', alpha=0.5)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
    fig.autofmt_xdate()
    ax1.legend(loc='best')

    ax2.plot(df['timestamp'], rsi_values, label='RSI', color='cyan')
    ax2.set_xlabel('Date', color='white')
    ax2.set_ylabel('RSI Value', color='white')
    ax2.axhline(y=70, color='red', linestyle='--', label='Overbought (70)')
    ax2.axhline(y=30, color='green', linestyle='--', label='Oversold (30)')
    ax2.fill_between(df['timestamp'], 70, 100, color='red', alpha=0.2)
    ax2.fill_between(df['timestamp'], 0, 30, color='green', alpha=0.2)
    ax2.grid(True, linestyle='--', alpha=0.5)
    ax2.legend(loc='best')

    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close(fig)
    buf.seek(0)
    return buf


async def rsi_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="لطفا نام یا نماد کوین مورد نظر خود را وارد کنید (مثال: bitcoin یا btc):"
    )
    return RSI_COIN


async def get_rsi_coin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    coin_query = update.message.text.strip()
    coin_id = find_coin_id(coin_query)
    await asyncio.sleep(1)
    if not coin_id:
        await update.message.reply_text("⚠️ کوین مورد نظر پیدا نشد. لطفا دوباره تلاش کنید.")
        return RSI_COIN

    context.user_data['coin_id'] = coin_id

    keyboard = [
        [
            InlineKeyboardButton("1 روز (30 دقیقه)", callback_data="rsi_days_1"),
            InlineKeyboardButton("7 روز (4 ساعت)", callback_data="rsi_days_7"),
        ],
        [
            InlineKeyboardButton("14 روز (4 ساعت)", callback_data="rsi_days_14"),
            InlineKeyboardButton("30 روز (4 ساعت)", callback_data="rsi_days_30"),
        ],
        [
            InlineKeyboardButton("90 روز (4 روز)", callback_data="rsi_days_90"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"کوین **{coin_id}** انتخاب شد. لطفا یک بازه زمانی را انتخاب کنید:\n"
        f"**توجه:** دقت داده‌ها بر اساس بازه زمانی متفاوت است.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )
    return RSI_TIMEFRAME


async def get_rsi_timeframe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("در حال پردازش درخواست شما...")

    days = int(query.data.split('_')[-1])
    coin_id = context.user_data.get('coin_id')

    df = fetch_ohlc_history(coin_id, days)
    await asyncio.sleep(1)
    if df.empty or 'close' not in df.columns or 'timestamp' not in df.columns:
        await query.edit_message_text("❌ داده‌ای برای این کوین یافت نشد. لطفا دوباره تلاش کنید.")
        return ConversationHandler.END

    rsi_values = calculate_rsi(df, length=14)
    if rsi_values is None or rsi_values.empty or len(rsi_values) < 2 or pd.isna(rsi_values.iloc[-1]):
        await query.edit_message_text(
            "⚠️ محاسبه RSI امکان‌پذیر نبود یا داده کافی وجود ندارد. لطفا بازه زمانی دیگری را انتخاب کنید.")
        return ConversationHandler.END

    rsi_value = rsi_values.iloc[-1]
    last_price = df["close"].iloc[-1]

    returns = df["close"].pct_change().dropna()
    volatility = returns.std() if not returns.empty else 0.02

    risk_pct = volatility * 1.5
    reward_pct = volatility * 3

    signal, explanation, entry_price, stop_loss, take_profit, rr_ratio = (None,) * 6

    if rsi_value < 30:
        signal = "✅ سیگنال ورود به خرید (اشباع فروش)"
        explanation = (
            "شاخص RSI زیر ۳۰ قرار گرفته است که نشان‌دهنده شرایط اشباع فروش است. "
            "این وضعیت معمولاً به عنوان فرصت مناسب برای ورود به موقعیت خرید تلقی می‌شود، "
            "چون احتمال بازگشت قیمت به سمت بالا وجود دارد. "
            "با این حال، توصیه می‌شود قبل از ورود، به حجم معاملات و سایر شاخص‌های تکمیلی نیز توجه کنید. "
            "حد ضرر بر اساس نوسانات واقعی بازار و با حفظ نسبت ریسک به ریوارد منطقی تعیین شده است."
        )
        entry_price = last_price
        stop_loss = entry_price * (1 - risk_pct)
        take_profit = entry_price * (1 + reward_pct)

    elif rsi_value > 70:
        signal = "🔻 سیگنال خروج یا فروش (اشباع خرید)"
        explanation = (
            "شاخص RSI بالای ۷۰ است که نشان‌دهنده شرایط اشباع خرید است. "
            "این موقعیت معمولاً هشدار شروع اصلاح قیمت یا بازگشت روند نزولی محسوب می‌شود. "
            "تریدرهای حرفه‌ای در این شرایط معمولاً از موقعیت‌های خرید خارج می‌شوند یا "
            "با رعایت حد ضرر و مدیریت ریسک وارد موقعیت فروش می‌شوند. "
            "حد ضرر و حد سود بر اساس نوسانات واقعی بازار و تحلیل ریسک به ریوارد تعریف شده‌اند."
        )
        entry_price = last_price
        stop_loss = entry_price * (1 + risk_pct)
        take_profit = entry_price * (1 - reward_pct)

    else:
        signal = "🔄 بازار در محدوده تعادلی - توصیه به احتیاط"
        explanation = (
            "شاخص RSI بین ۳۰ تا ۷۰ قرار دارد که نشان‌دهنده وضعیت بدون روند مشخص یا تعادلی بازار است. "
            "در این شرایط، ورود به معامله صرفاً بر اساس RSI ریسک قابل توجهی دارد و ممکن است "
            "تریدرها منتظر دریافت سیگنال‌های قوی‌تر از سایر شاخص‌ها و تاییدیه‌ها بمانند. "
            "مدیریت ریسک و حفظ نقدینگی برای فرصت‌های بهتر، در اولویت قرار دارد."
        )
        entry_price = None
        stop_loss = None
        take_profit = None

    if entry_price and stop_loss and take_profit:
        risk_value = abs(entry_price - stop_loss)
        reward_value = abs(take_profit - entry_price)
        rr_ratio = reward_value / risk_value if risk_value > 0 else None
    else:
        rr_ratio = None

    msg = (
        f"📊 تحلیل تکنیکال **{coin_id.capitalize()}** بر اساس داده‌های {days} روز گذشته:\n"
        f"🔹 آخرین قیمت: `${format_number(last_price)}`\n"
        f"🔹 مقدار RSI: `{rsi_value:.2f}`\n\n"
        f"{signal}\n\n"
        f"{explanation}\n\n"
    )

    if rr_ratio:
        msg += (
            f"🎯 نقطه ورود پیشنهادی: `${format_number(entry_price)}`\n"
            f"🛑 حد ضرر (Stop Loss): `${format_number(stop_loss)}`\n"
            f"🏆 حد سود (Take Profit): `${format_number(take_profit)}`\n"
            f"⚖️ نسبت ریسک به ریوارد (R/R Ratio): `{rr_ratio:.2f}`\n\n"
            "💡 **توجه:** این تحلیل صرفا یک سیگنال احتمالی است. همیشه با مدیریت ریسک وارد معامله شوید و به حد ضرر پایبند باشید."
        )
    else:
        msg += "💡 در شرایط فعلی، برای جلوگیری از ریسک غیرضروری، بهتر است وارد معامله نشوید."

    chart_buffer = generate_rsi_chart(df, rsi_values, coin_id, days)
    await context.bot.send_photo(chat_id=update.effective_chat.id,
                                 photo=InputFile(chart_buffer, filename=f'{coin_id}_rsi_chart.png'))
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')

    return ConversationHandler.END
