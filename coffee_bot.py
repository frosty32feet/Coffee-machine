from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
filters, ContextTypes, ConversationHandler)
from datetime import datetime
import uuid
import nest_asyncio
import asyncio
nest_asyncio.apply()  # <-- Important line

async def main():
    pass  # Replace this with your actual main logic

if __name__ == "__main__":
    asyncio.run(main())

coffee_menu = {
    "Espresso": {"price": 4.00, "image": "https://upload.wikimedia.org/wikipedia/commons/4/45/A_small_cup_of_coffee.JPG"},
    "Cappuccino": {"price": 7.00, "image": "https://upload.wikimedia.org/wikipedia/commons/c/c8/Cappuccino_at_Sightglass_Coffee.jpg"},
    "Latte": {"price": 6.00, "image": "https://upload.wikimedia.org/wikipedia/commons/7/7c/Caffe_latte_with_heart_latte_art.jpg"},
    "Americano": {"price": 5.00, "image": "https://upload.wikimedia.org/wikipedia/commons/0/0b/Coffee_Americano.JPG"},
    "Mocha": {"price": 10.00, "image": "https://upload.wikimedia.org/wikipedia/commons/f/f6/Mocha_coffee.jpg"}
}

coffee_emoji = {
    "Espresso": "☕",
    "Cappuccino": "🍶",
    "Latte": "🥛",
    "Americano": "🇺🇸☕",
    "Mocha": "🍫"
}

size_emoji = {
    "Small": "🔹",
    "Medium": "🔸",
    "Large": "⭐"
}

SIZES = ["Small", "Medium", "Large"]
COFFEE, SIZE, MILK_SUGAR, SUGAR_STICKS, QUANTITY, PAYMENT, CARD = range(7)

def get_greeting():
    hour = datetime.now().hour
    if hour < 12:
        return "Good morning!"
    elif hour < 18:
        return "Good afternoon!"
    else:
        return "Good evening!"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    greeting = get_greeting()
    keyboard = [
        [InlineKeyboardButton(f"{coffee_emoji[name]} {name}", callback_data=name)]
        for name in coffee_menu
    ] + [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    
    await update.message.reply_text(
        f"{greeting} Welcome to CoffeeBot!\nChoose a coffee type:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COFFEE

async def choose_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await cancel(update, context)

    coffee_name = query.data
    context.user_data["coffee"] = coffee_name
    context.user_data["price"] = coffee_menu[coffee_name]["price"]

    await query.message.reply_photo(photo=coffee_menu[coffee_name]["image"], caption=f"✅ You chose {coffee_name}!")
    
    keyboard = [
        [InlineKeyboardButton(f"{size_emoji[size]} {size}", callback_data=size)]
        for size in SIZES
    ] + [[InlineKeyboardButton("❌ Cancel", callback_data="cancel")]]
    
    await query.message.reply_text("Choose a size:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SIZE

async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await cancel(update, context)

    context.user_data["size"] = query.data
    keyboard = [
        [InlineKeyboardButton("🥛 Milk", callback_data="milk")],
        [InlineKeyboardButton("🍬 Sugar", callback_data="sugar")],
        [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
    ]
    await query.message.reply_text("Would you like milk or sugar?", reply_markup=InlineKeyboardMarkup(keyboard))
    return MILK_SUGAR

async def milk_sugar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await cancel(update, context)

    choice = query.data
    context.user_data["milk_or_sugar"] = choice
    if choice == "sugar":
        await query.message.reply_text("How many sugar sticks? (0-5)")
        return SUGAR_STICKS
    else:
        context.user_data["sugar_sticks"] = 0
        await query.message.reply_text("How many cups would you like?")
        return QUANTITY

async def sugar_sticks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        sticks = int(update.message.text)
        if 0 <= sticks <= 5:
            context.user_data["sugar_sticks"] = sticks
            await update.message.reply_text("How many cups would you like?")
            return QUANTITY
        else:
            await update.message.reply_text("Enter a number between 0 and 5.")
            return SUGAR_STICKS
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return SUGAR_STICKS

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qty = int(update.message.text)
        if qty <= 0:
            await update.message.reply_text("Enter a number greater than 0.")
            return QUANTITY

        context.user_data["quantity"] = qty
        price = context.user_data["price"]
        sticks = context.user_data.get("sugar_sticks", 0)
        extra_sugar = 1 if sticks > 2 else 0
        total = 0

        for i in range(1, qty + 1):
            if i == 3:
                continue
            total += price + extra_sugar

        context.user_data["total"] = total
        order_id = str(uuid.uuid4())[:8]
        context.user_data["order_id"] = order_id

        summary = (
            f"📝 *Order Summary:*\n"
            f"☕ Coffee: {context.user_data['coffee']}\n"
            f"📏 Size: {context.user_data['size']}\n"
            f"🍬 Sugar Sticks: {sticks}\n"
            f"🔢 Quantity: {qty}\n"
            f"🧾 Order ID: #{order_id}\n"
            f"💰 Total: ${total:.2f}"
        )

        keyboard = [
            [InlineKeyboardButton("💵 Cash", callback_data="cash")],
            [InlineKeyboardButton("💳 Card", callback_data="card")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]

        await update.message.reply_markdown(summary)
        await update.message.reply_text("How would you like to pay?", reply_markup=InlineKeyboardMarkup(keyboard))
        return PAYMENT
    except ValueError:
        await update.message.reply_text("Please enter a valid number.")
        return QUANTITY

async def payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel":
        return await cancel(update, context)

    method = query.data
    if method == "card":
        keyboard = [
            [InlineKeyboardButton("💳 Visa", callback_data="Visa")],
            [InlineKeyboardButton("💳 Mastercard", callback_data="Mastercard")],
            [InlineKeyboardButton("❌ Cancel", callback_data="cancel")]
        ]
        await query.message.reply_text("Choose card type:", reply_markup=InlineKeyboardMarkup(keyboard))
        return CARD
    else:
        total = context.user_data["total"]
        await query.message.reply_text(f"No discount. Please pay ${total:.2f}. Enjoy your coffee! ☕")
        return ConversationHandler.END

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    card_type = query.data
    total = context.user_data["total"]
    if card_type == "Visa":
        discount = total * 0.05
        total -= discount
        await query.message.reply_text(f"✅ 5% discount with Visa applied. Please pay ${total:.2f}. Enjoy your coffee! ☕")
    else:
        await query.message.reply_text(f"No discount. Please pay ${total:.2f}. Enjoy your coffee! ☕")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.callback_query:
        await update.callback_query.message.reply_text("❌ Order canceled. Come back anytime!")
    else:
        await update.message.reply_text("❌ Order canceled. Come back anytime!")
    return ConversationHandler.END

if __name__ == "__main__":
    # Load the token securely (optional)
    # from dotenv import load_dotenv
    # load_dotenv()
    # token = os.getenv("TELEGRAM_BOT_TOKEN")

    app = ApplicationBuilder().token("7676216513:AAE-CSJqshRA_gop3xnvPGaC2KOzqCnqeS4").build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            COFFEE: [CallbackQueryHandler(choose_coffee)],
            SIZE: [CallbackQueryHandler(choose_size)],
            MILK_SUGAR: [CallbackQueryHandler(milk_sugar)],
            SUGAR_STICKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sugar_sticks)],
            QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
            PAYMENT: [CallbackQueryHandler(payment)],
            CARD: [CallbackQueryHandler(card)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True
    )
    # Use per_chat instead of per_message
conv = ConversationHandler(
    entry_points=[CommandHandler("start", start)],
    states={
        COFFEE: [CallbackQueryHandler(choose_coffee)],
        SIZE: [CallbackQueryHandler(choose_size)],
        MILK_SUGAR: [CallbackQueryHandler(milk_sugar)],
        SUGAR_STICKS: [MessageHandler(filters.TEXT & ~filters.COMMAND, sugar_sticks)],
        QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
        PAYMENT: [CallbackQueryHandler(payment)],
        CARD: [CallbackQueryHandler(card)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    per_chat=True  # ✅ default and works with mixed handler types
)

app.add_handler(conv)
app.run_polling()
    # app.run_webhook(
from telegram import BotCommand

async def set_commands(application):
    commands = [
        BotCommand("start", "Start a new coffee order ☕"),
        BotCommand("cancel", "Cancel the current order ❌"),
        BotCommand("menu", "View the coffee menu 📋"),
        BotCommand("orderstatus", "View your current order summary 🧾"),
        BotCommand("help", "Get help and see available commands 📖"),
        BotCommand("about", "Learn about this Coffee Bot 🤖"),
        # Optional ones:
        # BotCommand("feedback", "Send feedback ✉️"),
        # BotCommand("location", "Send your location for delivery 📍"),
        # BotCommand("repeat", "Reorder your last coffee ☕🔁"),
    ]