# handlers/riskreward_handler.py
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from services.metrics import calculate_risk_reward
from config import RISKREWARD_ENTRY, RISKREWARD_STOP, RISKREWARD_TARGET

async def riskreward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="لطفا قیمت ورود (entry price) را وارد کنید:"
    )
    return RISKREWARD_ENTRY


async def get_riskreward_entry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        entry = float(update.message.text)
        context.user_data['entry'] = entry
        await update.message.reply_text("لطفا قیمت حد ضرر (stop-loss) را وارد کنید:")
        return RISKREWARD_STOP
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفا یک عدد وارد کنید.")
        return RISKREWARD_ENTRY


async def get_riskreward_stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        stop = float(update.message.text)
        context.user_data['stop'] = stop
        await update.message.reply_text("لطفا قیمت هدف سود (profit target) را وارد کنید:")
        return RISKREWARD_TARGET
    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفا یک عدد وارد کنید.")
        return RISKREWARD_STOP


async def get_riskreward_target(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = float(update.message.text)
        entry = context.user_data.get('entry')
        stop = context.user_data.get('stop')

        rr_ratio, risk_val, reward_val, position_type = calculate_risk_reward(entry, stop, target)

        if position_type == "نامعتبر" or risk_val is None or reward_val is None:
            await update.message.reply_text(
                "❌ مقادیر وارد شده معتبر نیستند. لطفا اطمینان حاصل کنید که مقادیر برای یک پوزیشن لانگ یا شورت منطقی هستند."
            )
            return ConversationHandler.END

        position_text = "خرید (Long)" if position_type == "long" else "فروش (Short)"
        risk_reward_ratio = risk_val / reward_val if reward_val != 0 else float('inf')

        await update.message.reply_text(
            f"⚖️ تحلیل نسبت ریسک به ریوارد برای پوزیشن **{position_text}**:\n"
            f"ورود: {entry}\n"
            f"حد ضرر: {stop}\n"
            f"هدف سود: {target}\n"
            f"------------------\n"
            f"📉 مقدار ریسک: {risk_val:.2f}\n"
            f"📈 مقدار پاداش: {reward_val:.2f}\n"
            f"------------------\n"
            f"🔹 نسبت پاداش به ریسک (Reward/Risk): **{rr_ratio:.2f}**\n"
            f"🔸 نسبت ریسک به پاداش (Risk/Reward): **{risk_reward_ratio:.2f}**\n\n"
            f"این یعنی برای هر **۱** واحد ریسک، **{rr_ratio:.2f}** واحد پاداش می‌گیرید."
        )
        return ConversationHandler.END

    except ValueError:
        await update.message.reply_text("ورودی نامعتبر است. لطفا یک عدد وارد کنید.")
        return RISKREWARD_TARGET
