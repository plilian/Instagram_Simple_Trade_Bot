import io
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
from telegram import Update, InputFile, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from services.coingecko_api import find_coin_id, fetch_ohlc_history, fetch_market_data
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
    plt.savefig(buf, format='png')
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

    days = int(query.data.split('_')[-1])
    coin_id = context.user_data.get('coin_id')

    df = fetch_ohlc_history(coin_id, days)
    if df.empty or 'close' not in df.columns or 'timestamp' not in df.columns:
        await query.edit_message_text("❌ داده‌ای برای این کوین یافت نشد. لطفا دوباره تلاش کنید.")
        return ConversationHandler.END

    rsi_values = calculate_rsi(df, length=14)
    if rsi_values is None or rsi_values.empty or pd.isna(rsi_values.iloc[-1]):
        await query.edit_message_text("⚠️ محاسبه RSI امکان‌پذیر نبود. لطفا بازه زمانی دیگری را انتخاب کنید.")
        return ConversationHandler.END

    rsi_value = rsi_values.iloc[-1]
    last_price = df["close"].iloc[-1]

    market_data = fetch_market_data(coin_id)
    if not market_data:
        await query.edit_message_text("⚠️ داده بازار یافت نشد.")
        return ConversationHandler.END

    returns = df["close"].pct_change().dropna()
    volatility = returns.std() if not returns.empty else 0.02

    risk_pct = volatility * 2  #
    reward_pct = volatility * 4  #

    if rsi_value < 30:
        signal = "✅ سیگنال خرید (اشباع فروش)"
        entry_price = last_price
        stop_loss = entry_price * (1 - risk_pct)
        take_profit = entry_price * (1 + reward_pct)
        explanation = (
            "RSI کمتر از ۳۰ نشان‌دهنده منطقه اشباع فروش است. "
            "این سیگنال ورود به معامله خرید را پیشنهاد می‌کند.\n"
            f"حد ضرر به اندازه {risk_pct*100:.2f}% پایین‌تر از قیمت ورود تنظیم شده است "
            "تا در صورت حرکت نامطلوب بازار ضرر کنترل شود.\n"
            f"حد سود به اندازه {reward_pct*100:.2f}% بالاتر از قیمت ورود تنظیم شده است "
            "تا سود مناسبی هدف قرار گیرد."
        )
    elif rsi_value > 70:
        signal = "⚠️ سیگنال فروش (اشباع خرید) - پیشنهاد عدم ورود"
        entry_price = None
        stop_loss = None
        take_profit = None
        explanation = (
            "RSI بیشتر از ۷۰ نشان‌دهنده منطقه اشباع خرید است. "
            "در این شرایط ورود به معامله خرید توصیه نمی‌شود و بهتر است "
            "منتظر کاهش قیمت‌ها یا تغییر شرایط باشید."
        )
    else:
        signal = "🔄 بازار متعادل - توصیه به صبر یا مدیریت ریسک دقیق"
        entry_price = None
        stop_loss = None
        take_profit = None
        explanation = (
            "RSI بین ۳۰ تا ۷۰ نشان‌دهنده بازار متعادل است. "
            "در این شرایط ورود مستقیم توصیه نمی‌شود مگر اینکه مدیریت ریسک دقیقی داشته باشید."
        )

    if entry_price and stop_loss and take_profit:
        risk_value = entry_price - stop_loss
        reward_value = take_profit - entry_price
        rr_ratio = reward_value / risk_value if risk_value > 0 else None
    else:
        rr_ratio = None

    msg = (
        f"📊 تحلیل تکنیکال **{coin_id}** بر اساس داده‌های {days} روز گذشته:\n"
        f"🔹 آخرین قیمت: ${last_price:.4f}\n"
        f"🔹 مقدار RSI: {rsi_value:.2f}\n\n"
        f"{signal}\n\n"
        f"{explanation}\n\n"
    )

    if rr_ratio:
        msg += (
            f"🎯 نقطه ورود پیشنهادی: ${entry_price:.4f}\n"
            f"🛑 حد ضرر (Stop Loss): ${stop_loss:.4f} ({risk_pct*100:.2f}%)\n"
            f"🏆 حد سود (Take Profit): ${take_profit:.4f} ({reward_pct*100:.2f}%)\n"
            f"⚖️ نسبت ریسک به ریوارد: {rr_ratio:.2f}\n\n"
            "💡 همیشه با مدیریت ریسک وارد بازار شوید و به حد ضرر احترام بگذارید."
        )
    else:
        msg += "💡 در شرایط فعلی پیشنهاد می‌شود یا وارد نشوید یا ریسک را به دقت مدیریت کنید."

    chart_buffer = generate_rsi_chart(df, rsi_values, coin_id, days)
    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=InputFile(chart_buffer, filename=f'{coin_id}_rsi_chart.png'))
    await context.bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode='Markdown')

    return ConversationHandler.END
