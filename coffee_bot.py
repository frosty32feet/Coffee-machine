from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from datetime import datetime
import uuid
import os
coffee_menu = {
    "Espresso": {"price": 4.00,"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/45/A_small_cup_of_coffee.JPG/640px-A_small_cup_of_coffee.JPG"
    },
    "Cappuccino": {"price": 7.00,"image": "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c8/Cappuccino_at_Sightglass_Coffee.jpg/640px-Cappuccino_at_Sightglass_Coffee.jpg"
    },
    "Latte": {"price": 6.00,"image": "https://www.nescafe.com/mena/sites/default/files/2023-04/RecipeHero_CaramelLatte_1066x1066.jpg"
    },
    "Americano": {"price": 5.00,"image": "https://dolo.com.au/cdn/shop/articles/522979505-shutterstock_1973536478.jpg?v=1690528484"
    },
    "Mocha": {"price": 10.00,"image": "https://www.folgerscoffee.com/folgers/recipes/_Hero%20Images/Detail%20Pages/6330/image-thumb__6330__schema_image/CafeMocha-hero.61028a28.jpg"
    }
}
coffee_emoji = {
    "Espresso": "☕", "Cappuccino": "🍶", "Latte": "🥛", "Americano": "☕", "Mocha": "🍫"
}
size_emoji = {
    "Small": "🔹", "Medium": "🔸", "Large": "⭐"
}
SIZES = ["Small", "Medium", "Large"]
COFFEE, SIZE, MILK_SUGAR, SUGAR_STICKS, QUANTITY, PAYMENT, CARD = range(7)
order_history = {}

def get_greeting():
    hour = datetime.now().hour
    if hour < 12: return "Good morning"
    elif hour < 18: return "Good afternoon"
    else: return "Good evening"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name or "there"
    greeting = get_greeting()
    keyboard = [[InlineKeyboardButton(f"{coffee_emoji[name]} {name}", callback_data=name)] for name in coffee_menu]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    await update.message.reply_text(
        f"{greeting}, {user}! Welcome to CoffeeBot!\nChoose a coffee type:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return COFFEE

async def choose_coffee(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel(update, context)
    coffee_name = query.data
    context.user_data.update({"coffee": coffee_name, "price": coffee_menu[coffee_name]["price"]})
    await query.message.reply_photo(photo=coffee_menu[coffee_name]["image"], caption=f"✅ You chose {coffee_name}!")
    keyboard = [[InlineKeyboardButton(f"{size_emoji[size]} {size}", callback_data=size)] for size in SIZES]
    keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data="cancel")])
    await query.message.reply_text("Choose a size:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SIZE

async def choose_size(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "cancel": return await cancel(update, context)
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
    if query.data == "cancel": return await cancel(update, context)
    context.user_data["milk_or_sugar"] = query.data
    if query.data == "sugar":
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
        if qty <= 0: raise ValueError
        context.user_data["quantity"] = qty
        price = context.user_data["price"]
        sticks = context.user_data.get("sugar_sticks", 0)
        extra_sugar = 1 if sticks > 2 else 0
        total = (price + extra_sugar) * qty
        tax = total * 0.08
        total_with_tax = total + tax
        context.user_data["total"] = total_with_tax
        order_id = str(uuid.uuid4())[:8]
        context.user_data["order_id"] = order_id
        order_history[order_id] = context.user_data.copy()

        summary = (
            f"📝 *Order Summary:*\n"
            f"☕ Coffee: {context.user_data['coffee']}\n"
            f"📏 Size: {context.user_data['size']}\n"
            f"🍬 Sugar Sticks: {sticks}\n"
            f"🔢 Quantity: {qty}\n"
            f"🧾 Order ID: #{order_id}\n"
            f"💰 Total (incl. tax): ${total_with_tax:.2f}"
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
    if query.data == "cancel": return await cancel(update, context)
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
        await query.message.reply_text(f"No discount. Please pay ${total:.2f}. Your coffee will be ready in 5 minutes! ☕")
        return ConversationHandler.END

async def card(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    total = context.user_data["total"]
    if query.data == "Visa":
        discount = total * 0.05
        total -= discount
        await query.message.reply_text(f"✅ 5% discount with Visa applied. Pay ${total:.2f}. Ready in 5 minutes!")
    else:
        await query.message.reply_text(f"Pay ${total:.2f}. Your coffee will be ready shortly! ☕")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = "❌ Order canceled. Come back anytime!"
    if update.callback_query:
        await update.callback_query.message.reply_text(msg)
    else:
        await update.message.reply_text(msg)
    return ConversationHandler.END

if __name__ == "__main__":
    app = ApplicationBuilder().token("7676216513:AAE_Q6Srbb-wGta6T1x73xnWWFaHefXhjto").build()
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
)
app.add_handler(conv)
app.run_polling()
