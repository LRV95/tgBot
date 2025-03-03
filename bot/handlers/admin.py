"""Обработчики админских команд."""

import os
import csv
import openpyxl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging
from bot.constants import CITIES, TAGS
from bot.keyboards import get_moderation_menu_keyboard
from database.db import Database
from bot.states import (MAIN_MENU, MODERATOR_SEARCH_REGISTERED_USERS, WAIT_FOR_CSV, WAIT_FOR_EVENTS_CSV, MODERATION_MENU, MODERATOR_EVENT_NAME,
                        MODERATOR_EVENT_DATE, MODERATOR_EVENT_TIME, MODERATOR_EVENT_CITY, MODERATOR_EVENT_DESCRIPTION,
                        MODERATOR_EVENT_CONFIRMATION, MODERATOR_EVENT_PARTICIPATION_POINTS, MODERATOR_EVENT_TAGS,
                        MODERATOR_EVENT_CREATOR, MODERATOR_EVENT_CODE)
from datetime import datetime

logger = logging.getLogger(__name__)

db = Database()

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if user_record and user_record.get("role") == "admin":
        await update.message.reply_markdown_v2(
            "*👋 Привет, администратор\!* Доступные команды:\n"
            "• `/load_excel` \\- загрузить данные из Excel\n"
            "• `/set_admin <user_id>` \\- назначить администратора\n"
            "• `/set_moderator <user_id>` \\- назначить модератора\n"
            "• `/delete_user <user_id>` \\- удалить пользователя\n"
            "• `/find_user_id <user_id>` \\- найти пользователя по id\n"
            "• `/find_users_name <name>` \\- найти пользователей по имени/фамилии\n"
            "• `/find_users_email <email>` \\- найти пользователей по email\n"
            "• `/delete_me` \\- удалить свой аккаунт\n"
            "• `/ai_query <query>` \\- обработать запрос через ИИ\n"
            "• `/search_projects_tag <tag>` \\- поиск проектов по тегу\n"
            "• `/search_projects_name <name>` \\- поиск проектов по названию\n"
            "• `/search_events_tag <tag>` \\- поиск мероприятий по тегу\n"
            "• `/search_events_project <project name>` \\- поиск мероприятий по проекту\n"
            "• `/load_projects_csv` \\- загрузить CSV с проектами\n"
            "• `/load_events_csv` \\- загрузить CSV с мероприятиями"
        )
    else:
        await update.message.reply_markdown_v2("*🚫 У вас нет доступа к командам администратора\\.*")

async def load_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /load_excel."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not (user_record and user_record.get("role") == "admin"):
        await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде.*")
        return
    try:
        workbook = openpyxl.load_workbook("./data/events.xlsx")
        sheet = workbook.active
        count = 0
        for row in sheet.iter_rows(min_row=2, values_only=True):
            name, date, time_value, location, curator, description, code, tags = row
            if not name:
                continue
            db.add_project(name, curator, time_value, location, description, tags)
            count += 1
        await update.message.reply_markdown(f"*✅ Excel файл обработан успешно.* Добавлено проектов: _{count}_.")
    except Exception as e:
        await update.message.reply_markdown("*🚫 Произошла ошибка при обработке Excel файла.*")

async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /set_admin."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not (user_record and user_record.get("role") == "admin"):
        await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде.*")
        return
    try:
        target_user_id = int(context.args[0])
        db.update_user_role(target_user_id, "admin")
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} назначен администратором.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /set_admin <user_id>*")

async def set_moderator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /set_moderator."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not (user_record and user_record.get("role") == "admin"):
        await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде.*")
        return
    try:
        target_user_id = int(context.args[0])
        db.update_user_role(target_user_id, "moderator")
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} назначен модератором.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /set_moderator <user_id>*")

async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete_user."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not (user_record and user_record.get("role") in ["admin", "moderator"]):
        await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде.*")
        return
    try:
        target_user_id = int(context.args[0])
        db.delete_user(target_user_id)
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} удален.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /delete_user <user_id>*")

async def find_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_user_id."""
    try:
        target_user_id = int(context.args[0])
        user = db.find_user_by_id(target_user_id)
        if user is None:
            await update.message.reply_markdown("*❌ Пользователь не найден.*")
        else:
            await update.message.reply_markdown(f"*👤 Пользователь найден:*\n{user}")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /find_user_id <user_id>*")

async def find_users_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_users_name."""
    try:
        name = " ".join(context.args)
        users = db.find_users_by_name(name)
        if not users:
            await update.message.reply_markdown("*❌ Пользователи не найдены.*")
        else:
            message = "*👥 Найденные пользователи:*\n"
            for user in users:
                message += f"ID: {user['id']}, Имя: {user['first_name']} {user['last_name']}\n"
            await update.message.reply_markdown(message)
    except Exception:
        await update.message.reply_markdown("*🚫 Ошибка при поиске пользователей по имени.*")

async def find_users_email(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_users_email."""
    try:
        email = " ".join(context.args)
        users = db.find_users_by_email(email)
        if not users:
            await update.message.reply_markdown("*❌ Пользователи не найдены.*")
        else:
            message = "*📧 Найденные пользователи:*\n"
            for user in users:
                message += f"ID: {user['id']}, Email: {user['email']}\n"
            await update.message.reply_markdown(message)
    except Exception:
        await update.message.reply_markdown("*🚫 Ошибка при поиске пользователей по email.*")

async def load_projects_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /load_projects_csv."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not (user_record and user_record.get("role") == "admin"):
        await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде.*")
        return MAIN_MENU
    await update.message.reply_markdown("*📥 Пожалуйста, отправьте CSV файл с данными о проектах (расширение .csv).*")
    return WAIT_FOR_CSV

async def process_csv_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки CSV файла с проектами."""
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        data_folder = os.path.join(".", "data")
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        temp_path = os.path.join(data_folder, update.message.document.file_name)
        await file.download_to_drive(custom_path=temp_path)
        count = 0
        with open(temp_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get("Проект")
                curator = row.get("Ответственный")
                phone_number = row.get("Телефон")
                email = row.get("Почта")
                description = row.get("Суть проекта")
                tags = row.get("Теги", "")
                if not name:
                    continue
                db.add_project(name, curator, phone_number, email, description, tags)
                count += 1
        os.remove(temp_path)
        await update.message.reply_markdown(f"*✅ CSV файл обработан успешно.* Добавлено проектов: _{count}_.")
    except Exception as e:
        await update.message.reply_markdown("*🚫 Произошла ошибка при обработке CSV файла.*")
    return MAIN_MENU

async def load_events_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /load_events_csv."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not (user_record and user_record.get("role") == "admin"):
        await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде.*")
        return MAIN_MENU
    await update.message.reply_markdown("*📥 Пожалуйста, отправьте CSV файл с данными о мероприятиях (расширение .csv).*")
    return WAIT_FOR_EVENTS_CSV

async def process_events_csv_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки CSV файла с мероприятиями."""
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        data_folder = os.path.join(".", "data")
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        temp_path = os.path.join(data_folder, update.message.document.file_name)
        await file.download_to_drive(custom_path=temp_path)
        count = 0
        await update.message.reply_markdown("*📥 Обрабатываем CSV файл с мероприятиями...*")
        with open(temp_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get("Название", "")
                event_date = row.get("Дата", "")
                start_time = row.get("Время", "")
                city = row.get("Локация", "")
                creator = row.get("Организатор", "")
                description = row.get("Описание", "")
                participation_points = row.get("Ценность", "")
                tags = row.get("Теги", "")
                code = row.get("Код", "")
                owner = "admin"
                
                if participation_points == "":
                    participation_points = 5
                
                # Добавляем мероприятие в базу данных
                try:
                    db.add_event(
                        name=name,
                        event_date=event_date, 
                        start_time=start_time, 
                        city=city,
                        creator=creator,
                        description=description,
                        participation_points=int(participation_points),
                        tags=tags,
                        code=code,
                        owner=owner
                    )
                    count += 1
                    await update.message.reply_markdown(f"*✅ Мероприятие {name} добавлено в базу данных.*")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении мероприятия: {e}")
                    
        os.remove(temp_path)
        await update.message.reply_markdown(f"*✅ CSV файл обработан успешно.* Добавлено мероприятий: _{count}_.")
    except Exception as e:
        logger.error(f"Ошибка при обработке CSV файла с мероприятиями: {e}")
        await update.message.reply_markdown("*🚫 Произошла ошибка при обработке CSV файла с мероприятиями.*")
    return MAIN_MENU

async def moderation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_record = db.get_user(user.id)
    if user_record and user_record.get("role") in ["admin", "moderator"]:
        await update.message.reply_text("Меню модерирования:", reply_markup=get_moderation_menu_keyboard())
        return MODERATION_MENU
    else:
        await update.message.reply_text("🚫 У вас недостаточно прав для доступа к модерационному меню.")
        return MAIN_MENU


async def handle_moderation_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора в меню модерации."""
    text = update.message.text
    
    if text == "Создать мероприятие":
        await update.message.reply_text("Введите название мероприятия:")
        return MODERATOR_EVENT_NAME
        
    elif text == "Просмотреть мероприятия":
        return await moderator_view_events(update, context)
        
    elif text == "Удалить мероприятие":
        return await moderator_delete_event(update, context)
        
    elif text == "Найти пользователей":
        await update.message.reply_text("Введите ID мероприятия для поиска зарегистрированных пользователей:")
        return MODERATOR_SEARCH_REGISTERED_USERS
        
    elif text == "Список мероприятий":
        return await moderator_list_all_events(update, context)
        
    elif text == "Вернуться в главное меню":
        from bot.keyboards import get_main_menu_keyboard
        user_record = db.get_user(update.effective_user.id)
        role = user_record.get("role") if user_record else "user"
        await update.message.reply_text(
            "Возвращаемся в главное меню.",
            reply_markup=get_main_menu_keyboard(role=role)
        )
        return MAIN_MENU
        
    else:
        await update.message.reply_text(
            "Неизвестная команда. Выберите действие из меню.",
            reply_markup=get_moderation_menu_keyboard()
        )
        return MODERATION_MENU

async def moderator_create_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запускает диалог создания мероприятия модератором."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not user_record or user_record.get("role") not in ["admin", "moderator"]:
        await update.message.reply_text("🚫 У вас недостаточно прав для создания мероприятия.")
        return MAIN_MENU
    await update.message.reply_text("Введите название мероприятия:")
    return MODERATOR_EVENT_NAME

async def moderator_handle_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_name"] = update.message.text.strip()
    await update.message.reply_text("Введите дату мероприятия (ГГГГ-ММ-ДД):")
    return MODERATOR_EVENT_DATE

async def moderator_handle_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_date"] = update.message.text.strip()
    await update.message.reply_text("Введите время мероприятия (ЧЧ:ММ):")
    return MODERATOR_EVENT_TIME

async def moderator_handle_event_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_time"] = update.message.text.strip()
    await update.message.reply_text(f"Введите локацию проведения мероприятия из доступных: {', '.join(CITIES)}.")
    return MODERATOR_EVENT_CITY

async def moderator_handle_event_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_city"] = update.message.text.strip()
    if context.user_data["event_city"] not in CITIES:
        await update.message.reply_text(f"Локация {context.user_data['event_city']} не найдена в списке доступных. Попробуйте снова.")
        return MODERATOR_EVENT_CITY
    await update.message.reply_text("Введите организатора мероприятия:")
    return MODERATOR_EVENT_CREATOR

async def moderator_handle_event_creator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_creator"] = update.message.text.strip()
    await update.message.reply_text("Введите описание мероприятия:")
    return MODERATOR_EVENT_DESCRIPTION

async def moderator_handle_event_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_description"] = update.message.text.strip()
    await update.message.reply_text("Введите ценность мероприятия:")
    return MODERATOR_EVENT_PARTICIPATION_POINTS

async def moderator_handle_event_participation_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_participation_points"] = update.message.text.strip()
    if not context.user_data["event_participation_points"].isdigit():
        await update.message.reply_text("Ценность мероприятия должна быть числом. Попробуйте снова.")
        return MODERATOR_EVENT_PARTICIPATION_POINTS
    await update.message.reply_text(f"Введите теги мероприятия (через запятую) из доступных тегов: {', '.join(TAGS)}.")
    return MODERATOR_EVENT_TAGS

async def moderator_handle_event_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_tags"] = update.message.text.replace(" ", "")
    if not all(tag in TAGS for tag in context.user_data["event_tags"].split(",")):
        await update.message.reply_text(f"Теги должны быть из списка доступных тегов: {', '.join(TAGS)}. Попробуйте снова.")
        return MODERATOR_EVENT_TAGS
    await update.message.reply_text("Введите код для мероприятия (один для всех пользователей):")
    return MODERATOR_EVENT_CODE

async def moderator_handle_event_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_code"] = update.message.text.strip()
    summary = (
        f"Название: {context.user_data['event_name']}\n"
        f"Дата: {context.user_data['event_date']}\n"
        f"Время: {context.user_data['event_time']}\n"
        f"Локация: {context.user_data['event_city']}\n"
        f"Организатор: {context.user_data['event_creator']}\n"
        f"Описание: {context.user_data['event_description']}\n"
        f"Ценность: {context.user_data['event_participation_points']}\n"
        f"Теги: {context.user_data['event_tags']}\n"
        f"Код: {context.user_data['event_code']}\n\n"
        "Подтверждаете создание мероприятия? (Да/Нет)"
    )
    await update.message.reply_text(summary)
    return MODERATOR_EVENT_CONFIRMATION


async def moderator_confirm_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()
    if response not in ["да", "yes"]:
        await update.message.reply_text("Создание мероприятия отменено.")
        return MODERATION_MENU
    user = update.effective_user
    event_name = context.user_data.get("event_name")
    event_date = context.user_data.get("event_date")
    event_time = context.user_data.get("event_time")
    event_city = context.user_data.get("event_city")
    event_creator = context.user_data.get("event_creator")
    event_description = context.user_data.get("event_description")
    event_participation_points = context.user_data.get("event_participation_points")
    event_tags = context.user_data.get("event_tags")
    event_code = context.user_data.get("event_code")
    owner = f"moderator:{user.id}"
    try:
        db.add_event(
            name=event_name,
            event_date=event_date,
            start_time=event_time,
            city=event_city,
            creator=event_creator,
            description=event_description,
            participation_points=event_participation_points,
            tags=event_tags,
            code=event_code,
            owner=owner
        )
        await update.message.reply_text("Мероприятие успешно создано!")
    except Exception as e:
        logger.error(f"Ошибка при создании мероприятия: {e}")
        await update.message.reply_text(f"Ошибка при создании мероприятия: {e}")
    # Очищаем временные данные
    for key in ["event_name", "event_date", "event_time", "event_city", "event_description", "event_code", "event_participation_points", "event_tags", "event_creator"]:
        context.user_data.pop(key, None)
    return MODERATION_MENU

# Просмотр пользователей, зарегистрированных на мероприятие модератора
async def moderator_view_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список мероприятий, созданных модератором, с кнопками для просмотра зарегистрированных пользователей."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not user_record or user_record.get("role") not in ["admin", "moderator"]:
        await update.message.reply_text("🚫 У вас недостаточно прав для просмотра мероприятий.")
        return MAIN_MENU

    # Для админа показываем все мероприятия, для модератора - только его
    if user_record.get("role") == "admin":
        events = db.get_all_events()
    else:
        owner_str = f"moderator:{user.id}"
        events = [event for event in db.get_all_events() if event.get("owner") == owner_str]

    if not events:
        await update.message.reply_text("Нет доступных мероприятий.")
        return MODERATION_MENU
    keyboard = []
    for event in events:
        button_text = f"{event['name']} ({event.get('event_date')})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_event_users:{event['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите мероприятие для просмотра зарегистрированных пользователей:", reply_markup=reply_markup)
    return MODERATION_MENU

async def moderator_handle_view_event_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие кнопки просмотра зарегистрированных пользователей."""
    query = update.callback_query
    await query.answer()
    event_id = query.data.split(":", 1)[1]
    users = db.get_users_for_event(event_id)
    if not users:
        await query.edit_message_text("На данном мероприятии нет зарегистрированных пользователей.")
    else:
        message = "Зарегистрированные пользователи:\n"
        for u in users:
            message += f"ID: {u['id']}, Имя: {u['first_name']}\n"
        await query.edit_message_text(message)
    return MODERATION_MENU

async def moderator_delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список мероприятий модератора с кнопками для удаления."""
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not user_record or user_record.get("role") not in ["admin", "moderator"]:
        await update.message.reply_text("🚫 У вас недостаточно прав для удаления мероприятий.")
        return MAIN_MENU

    # Для админа показываем все мероприятия, для модератора - только его
    if user_record.get("role") == "admin":
        events = db.get_all_events()
    else:
        creator_str = f"moderator:{user.id}"
        events = [event for event in db.get_all_events() if event.get("creator") == creator_str]

    if not events:
        await update.message.reply_text("Нет доступных мероприятий для удаления.")
        return MODERATION_MENU
    keyboard = []
    for event in events:
        button_text = f"{event['name']} ({event.get('event_date')})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_event:{event['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите мероприятие для удаления:", reply_markup=reply_markup)
    return MODERATION_MENU

async def moderator_handle_delete_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие кнопки удаления мероприятия."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID мероприятия из callback_data
    event_id = int(query.data.split(":", 1)[1])
    
    # Проверяем права пользователя
    user = update.effective_user
    user_record = db.get_user(user.id)
    if not user_record or user_record.get("role") not in ["admin", "moderator"]:
        await query.edit_message_text("🚫 У вас нет прав на удаление мероприятий.")
        return MODERATION_MENU

    # Получаем информацию о мероприятии
    event = db.get_event_by_id(event_id)
    if not event:
        await query.edit_message_text("❌ Мероприятие не найдено.")
        return MODERATION_MENU

    # Проверяем, может ли модератор удалить это мероприятие
    if user_record.get("role") == "moderator" and event.get("owner") != f"moderator:{user.id}":
        await query.edit_message_text("🚫 Вы можете удалять только свои мероприятия.")
        return MODERATION_MENU

    try:
        # Удаляем мероприятие
        db.delete_event(event_id)
        await query.edit_message_text(f"✅ Мероприятие \"{event.get('name')}\" успешно удалено.")
    except Exception as e:
        logger.error(f"Ошибка при удалении мероприятия: {e}")
        await query.edit_message_text("❌ Произошла ошибка при удалении мероприятия.")
    
    return MODERATION_MENU

async def moderator_handle_search_event_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_id_text = update.message.text.strip()
    try:
        event_id = int(event_id_text)
    except ValueError:
        await update.message.reply_text("Неверный формат ID мероприятия. Введите числовое значение.")
        return MODERATOR_SEARCH_REGISTERED_USERS

    # Получаем информацию о мероприятии по его ID
    event = db.get_event_by_id(event_id)
    if not event:
        await update.message.reply_text("Мероприятие не найдено.")
        return MODERATION_MENU

    # Извлекаем название и код мероприятия из поля tags
    name = event.get("name")
    code = event.get("code")

    # Формируем заголовок с названием и кодом мероприятия
    message = f"Мероприятие: {name}"
    message += f" (Код: {code})"
    message += "\n\nЗарегистрированные пользователи:\n"

    # Получаем пользователей, зарегистрированных на мероприятие
    users = db.get_users_for_event(event_id)
    if not users:
        message += "Нет зарегистрированных пользователей."
    else:
        for u in users:
            message += f"ID: {u['id']}, Имя: {u['first_name']}\n"
    await update.message.reply_text(message)
    return MODERATION_MENU

async def moderator_search_event_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ID мероприятия для поиска зарегистрированных пользователей:")
    return MODERATOR_SEARCH_REGISTERED_USERS

async def moderator_list_all_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    events = db.get_all_events()
    if not events:
        await update.message.reply_text("Нет доступных мероприятий.")
        return MODERATION_MENU

    message_lines = []
    for event in events:
        id = event.get("id")
        name = event.get("name")
        code = event.get("code")

        message_lines.append(f"ID: {id}, Название: {name} (Код: {code})")


    message_text = "\n".join(message_lines)
    await update.message.reply_text(message_text)
    return MODERATION_MENU
