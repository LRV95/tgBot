"""Общие обработчики команд бота."""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.keyboards import get_main_menu_keyboard
from bot.states import MAIN_MENU
from database.db import Database
from config import ADMIN_ID

db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    
    if not user_record:
        role = "admin" if user.id in ADMIN_ID else "guest"
        db.save_user(user.id, user.first_name or "", user.last_name or "", "", "", 0, "", role)
        if role == "admin":
            await update.message.reply_markdown("*✅ Вы зарегистрированы! Вы администратор.* 🎉")
        else:
            await update.message.reply_markdown("*👋 Добро пожаловать, гость!*")
    else:
        if user_record.get("role") == "user" and user.id in ADMIN_ID:
            db.update_user_role(user.id, "admin")
        if user_record.get("role") == "admin":
            await update.message.reply_markdown("*👋 С возвращением, администратор!*")
        else:
            await update.message.reply_markdown("*👋 С возвращением!*")
    
    role = db.get_user(user.id).get("role", "guest")
    keyboard = get_main_menu_keyboard(role)
    await update.message.reply_markdown("*📌 Выберите раздел:*", reply_markup=keyboard)
    return MAIN_MENU

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /cancel."""
    await update.message.reply_markdown("*↩️ Возвращаемся в главное меню.*")
    role = db.get_user(update.effective_user.id).get("role", "user")
    keyboard = get_main_menu_keyboard(role)
    await update.message.reply_markdown("Выберите раздел:", reply_markup=keyboard)
    return MAIN_MENU
