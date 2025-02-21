"""Общие обработчики команд бота."""

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.keyboards import get_main_menu_keyboard
from bot.states import MAIN_MENU
from database.db import Database
from config import ADMIN_ID
import logging

logger = logging.getLogger(__name__)
db = Database()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    
    logger.info(f"Пользователь {user.id} начал взаимодействие с ботом")
    logger.info(f"Имя пользователя: {user.first_name}")
    
    if not user_record:
        role = "admin" if user.id in ADMIN_ID else "user"
        first_name = user.first_name if user.first_name else None
        logger.info(f"Сохраняем нового пользователя: id={user.id}, first_name={first_name}, role={role}")
        db.save_user(user.id, first_name, role)
        greeting = first_name if first_name else "Пользователь"
        if role == "admin":
            await update.message.reply_markdown(f"*✅ {greeting}, вы зарегистрированы как администратор!* 🎉")
        else:
            await update.message.reply_markdown(f"*👋 Добро пожаловать, {greeting}!*")
    else:
        # Обновляем имя если оно изменилось
        current_first_name = user.first_name if user.first_name else None
        if current_first_name != user_record.get("first_name"):
            logger.info(f"Обновляем имя пользователя {user.id}: {current_first_name}")
            db.update_first_name(user.id, current_first_name)
        
        if user_record.get("role") == "user" and user.id in ADMIN_ID:
            db.update_user_role(user.id, "admin")
            
        greeting = user.first_name if user.first_name else "Пользователь"
        if user_record.get("role") == "admin":
            await update.message.reply_markdown(f"*👋 С возвращением, {greeting}!*")
        else:
            await update.message.reply_markdown(f"*👋 С возвращением, {greeting}!*")
    
    role = db.get_user(user.id).get("role", "user")
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
