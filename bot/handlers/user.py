"""Обработчики пользовательских команд."""

from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import (
    MAIN_MENU, AI_CHAT, VOLUNTEER_HOME, GUEST_HOME,
    GUEST_REGISTRATION, GUEST_TAG_SELECTION,
    PROFILE_MENU, WAIT_FOR_PROFILE_UPDATE,
    PROFILE_TAG_SELECTION, PROFILE_UPDATE_SELECTION
)
from bot.keyboards import (
    get_main_menu_keyboard,
    get_volunteer_home_keyboard,
    get_profile_menu_keyboard,
    get_tag_selection_keyboard
)
from database.db import Database
from services.ai_service import ContextRouterAgent

db = Database()

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик главного меню."""
    user = update.effective_user
    role = db.get_user(user.id).get("role", "guest")
    choice = update.message.text.strip()
    
    if role == "guest":
        if choice == "Регистрация":
            await update.message.reply_markdown("*Пожалуйста, введите ваши данные в формате: Имя, Фамилия, Email*")
            return GUEST_REGISTRATION
        elif choice == "🤖 ИИ Помощник":
            exit_keyboard = ReplyKeyboardMarkup([["Выход."]], resize_keyboard=True)
            await update.message.reply_markdown("Введите ваш запрос для ИИ Помощника:", reply_markup=exit_keyboard)
            return AI_CHAT
        elif choice == "Мероприятия":
            events = db.get_all_events()
            if events:
                message = "*Список мероприятий:*\n"
                for event in events:
                    message += f"ID: {event['id']}, Дата: {event['event_date']}, Время: {event['start_time']}, Создатель: {event['creator']}, Теги: {event['tags']}\n"
                await update.message.reply_markdown(message)
            else:
                await update.message.reply_markdown("*На данный момент мероприятий нет.*")
            await update.message.reply_markdown("Выберите опцию:", reply_markup=get_main_menu_keyboard("guest"))
            return GUEST_HOME
        elif choice == "Выход":
            await update.message.reply_markdown("*До свидания!*")
            return ConversationHandler.END
        else:
            await update.message.reply_markdown("*⚠️ Пожалуйста, выберите один из предложенных вариантов.*")
            return GUEST_HOME
    else:
        if "Дом Волонтера" in choice:
            await update.message.reply_markdown("*🏠 Добро пожаловать в Дом Волонтера.*", reply_markup=get_volunteer_home_keyboard())
            return VOLUNTEER_HOME
        elif "ИИ Волонтера" in choice:
            exit_keyboard = ReplyKeyboardMarkup([["Выход."]], resize_keyboard=True)
            await update.message.reply_markdown("Введите ваш запрос для ИИ Волонтера:", reply_markup=exit_keyboard)
            return AI_CHAT
        else:
            await update.message.reply_markdown("*⚠️ Пожалуйста, выберите один из предложенных вариантов.*")
            return MAIN_MENU

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик чата с ИИ."""
    text = update.message.text.strip()
    if text == "Выход.":
        role = db.get_user(update.effective_user.id).get("role", "user")
        keyboard = get_main_menu_keyboard(role)
        await update.message.reply_markdown("Возвращаемся в главное меню:", reply_markup=keyboard)
        return MAIN_MENU
    else:
        agent = ContextRouterAgent()
        response = agent.process_query(text, update.effective_user.id)
        await update.message.reply_markdown(response)
        exit_keyboard = ReplyKeyboardMarkup([["Выход."]], resize_keyboard=True)
        return AI_CHAT

async def handle_volunteer_home(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик домашнего экрана волонтера."""
    text = update.message.text.strip()
    if text == "Выход.":
        role = db.get_user(update.effective_user.id).get("role", "user")
        keyboard = get_main_menu_keyboard(role)
        await update.message.reply_markdown("Возвращаемся в главное меню:", reply_markup=keyboard)
        return MAIN_MENU
    elif text == "Профиль":
        await update.message.reply_markdown("*Выберите пункт профиля:*", reply_markup=get_profile_menu_keyboard())
        return PROFILE_MENU
    else:
        await update.message.reply_markdown(f"*{text} - Функционал в разработке.*")
        await update.message.reply_markdown("Выберите опцию:", reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME

async def handle_guest_registration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик регистрации гостя."""
    text = update.message.text.strip()
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 3:
        await update.message.reply_markdown("*⚠️ Неверный формат. Введите данные через запятую: Имя, Фамилия, Email*")
        return GUEST_REGISTRATION
    
    first_name, last_name, email = parts
    user = update.effective_user
    db.save_user(user.id, first_name, last_name, email, "", 0, "", "user")
    await update.message.reply_markdown("*✅ Вы успешно зарегистрированы!*")
    
    context.user_data['selected_tags'] = []
    keyboard = get_tag_selection_keyboard()
    await update.message.reply_markdown("*Выберите интересующие вас теги:*", reply_markup=keyboard)
    return GUEST_TAG_SELECTION

async def handle_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора тегов при регистрации."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data.startswith("tag:"):
        tag = data.split(":", 1)[1]
        selected = context.user_data.get('selected_tags', [])
        if tag in selected:
            selected.remove(tag)
        else:
            selected.append(tag)
        context.user_data['selected_tags'] = selected
        
        text = "*Выберите интересующие вас теги:*\n"
        text += "Выбрано: " + ", ".join(selected) if selected else "Ничего не выбрано."
        keyboard = get_tag_selection_keyboard(selected)
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")
        return GUEST_TAG_SELECTION
    
    elif data == "done":
        user = update.effective_user
        selected = context.user_data.get('selected_tags', [])
        tags_str = ", ".join(selected)
        current_user = db.get_user(user.id)
        if current_user:
            db.save_user(
                user.id,
                current_user.get("first_name", ""),
                current_user.get("last_name", ""),
                current_user.get("email", ""),
                current_user.get("registered_events", ""),
                current_user.get("score", 0),
                current_user.get("used_codes", ""),
                current_user.get("role", "user"),
                tags_str
            )
        await query.edit_message_text(text="*✅ Теги сохранены: " + tags_str + "*", parse_mode="Markdown")
        keyboard = get_main_menu_keyboard("user")
        await query.message.reply_markdown("*📌 Выберите раздел:*", reply_markup=keyboard)
        return MAIN_MENU

async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик меню профиля."""
    text = update.message.text.strip()
    if text == "Информация":
        user = db.get_user(update.effective_user.id)
        if user:
            profile_message = ("*Ваш профиль:*\n"
                             f"Имя: {user.get('first_name', 'Не указано')}\n"
                             f"Фамилия: {user.get('last_name', 'Не указано')}\n"
                             f"Email: {user.get('email', 'Не указано')}\n"
                             f"Роль: {user.get('role', 'Не указано')}\n"
                             f"Счёт: {user.get('score', 0)}\n"
                             f"Теги: {user.get('tags', 'Не указаны')}")
            await update.message.reply_markdown(profile_message)
        else:
            await update.message.reply_markdown("*Профиль не найден.*")
        await update.message.reply_markdown("*Выберите пункт профиля:*", reply_markup=get_profile_menu_keyboard())
        return PROFILE_MENU
    
    elif text == "Изменить информацию":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Контактная информация", callback_data="update:contact")],
            [InlineKeyboardButton("Теги", callback_data="update:tags")]
        ])
        await update.message.reply_markdown("*Выберите, что хотите изменить:*", reply_markup=keyboard)
        return PROFILE_UPDATE_SELECTION
    
    elif text == "Выход":
        await update.message.reply_markdown("*Возвращаемся в Дом Волонтера.*", reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    
    else:
        await update.message.reply_markdown("*Пожалуйста, выберите один из предложенных пунктов.*", reply_markup=get_profile_menu_keyboard())
        return PROFILE_MENU

async def handle_profile_update_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора типа обновления профиля."""
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == "update:contact":
        await query.edit_message_text(text="*Введите новые данные в формате: Имя, Фамилия, Email*", parse_mode="Markdown")
        return WAIT_FOR_PROFILE_UPDATE
    elif data == "update:tags":
        user = update.effective_user
        current_user = db.get_user(user.id)
        if current_user and current_user.get("tags"):
            context.user_data['selected_tags'] = [tag.strip() for tag in current_user.get("tags", "").split(",") if tag.strip()]
        else:
            context.user_data['selected_tags'] = []
        
        keyboard = get_tag_selection_keyboard(context.user_data['selected_tags'])
        init_text = "*Выберите интересующие вас теги:*\n"
        init_text += "Выбрано: " + ", ".join(context.user_data['selected_tags']) if context.user_data['selected_tags'] else "Ничего не выбрано."
        await query.edit_message_text(text=init_text, reply_markup=keyboard, parse_mode="Markdown")
        return PROFILE_TAG_SELECTION

async def handle_contact_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обновления контактной информации."""
    text = update.message.text.strip()
    parts = [part.strip() for part in text.split(",")]
    if len(parts) != 3:
        await update.message.reply_markdown("*⚠️ Неверный формат. Введите данные через запятую: Имя, Фамилия, Email*")
        return WAIT_FOR_PROFILE_UPDATE
    
    first_name, last_name, email = parts
    user = update.effective_user
    current_user = db.get_user(user.id)
    if current_user:
        db.save_user(
            user.id,
            first_name,
            last_name,
            email,
            current_user.get("registered_events", ""),
            current_user.get("score", 0),
            current_user.get("used_codes", ""),
            current_user.get("role", "user"),
            current_user.get("tags", "")
        )
    await update.message.reply_markdown("*✅ Контактная информация обновлена!*")
    keyboard = get_main_menu_keyboard(current_user.get("role", "user"))
    await update.message.reply_markdown("*📌 Выберите раздел:*", reply_markup=keyboard)
    return MAIN_MENU

async def handle_profile_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик выбора тегов при обновлении профиля."""
    query = update.callback_query
    await query.answer()
    data = query.data
    selected = context.user_data.get('selected_tags', [])
    
    if data.startswith("tag:"):
        tag = data.split(":", 1)[1]
        if tag in selected:
            selected.remove(tag)
        else:
            selected.append(tag)
        context.user_data['selected_tags'] = selected
        
        text = "*Выберите интересующие вас теги:*\n"
        text += "Выбрано: " + ", ".join(selected) if selected else "Ничего не выбрано."
        keyboard = get_tag_selection_keyboard(selected)
        await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")
        return PROFILE_TAG_SELECTION
    
    elif data == "done_tags":
        user = update.effective_user
        selected = context.user_data.get('selected_tags', [])
        tags_str = ", ".join(selected)
        current_user = db.get_user(user.id)
        if current_user:
            db.save_user(
                user.id,
                current_user.get("first_name", ""),
                current_user.get("last_name", ""),
                current_user.get("email", ""),
                current_user.get("registered_events", ""),
                current_user.get("score", 0),
                current_user.get("used_codes", ""),
                current_user.get("role", "user"),
                tags_str
            )
        await query.edit_message_text(text="*✅ Профиль обновлён. Теги: " + tags_str + "*", parse_mode="Markdown")
        keyboard = get_main_menu_keyboard(current_user.get("role", "user"))
        await query.message.reply_markdown("*📌 Выберите раздел:*", reply_markup=keyboard)
        return MAIN_MENU
