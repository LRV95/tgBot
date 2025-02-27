"""Обработчики админских команд."""

import os
import csv
import openpyxl
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import logging
from database.db import Database
from bot.states import (MAIN_MENU, WAIT_FOR_CSV, WAIT_FOR_EVENTS_CSV, MODERATION_MENU, MODERATOR_EVENT_NAME,
                        MODERATOR_EVENT_DATE, MODERATOR_EVENT_TIME, MODERATOR_EVENT_CITY, MODERATOR_EVENT_DESCRIPTION,
                        MODERATOR_EVENT_CONFIRMATION, MAIN_MENU, MODERATOR_SEARCH_REGISTERED_USERS)

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
        with open(temp_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get("Название", "")
                event_date = row.get("Дата", "")
                start_time = row.get("Время", "")
                city = row.get("Локация", "")
                creator = row.get("Организатор", "")
                description = row.get("Описание", "")
                
                # Получаем стоимость (ценность) мероприятия
                try:
                    participation_points = int(row.get("Ценность", "100").strip())
                except (ValueError, TypeError):
                    participation_points = 100  # Значение по умолчанию
                
                if not name or not event_date or not start_time or not city or not creator:
                    continue
                
                # TODO: Заполнение тегов будет реализовано через AI агента
                # Теги будут выбираться из списка констант в bot/constants.py
                # Временно сохраняем базовую информацию о мероприятии
                tags = f"Название: {name}; Локация: {city}; Описание: {description}"
                
                # Добавляем мероприятие в базу данных
                try:
                    db.add_event_detail(
                        project_id=None, 
                        event_date=event_date, 
                        start_time=start_time, 
                        participants_count=0, 
                        participation_points=participation_points, 
                        creator=creator, 
                        tags=tags,
                        city=city
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
        from bot.keyboards import get_moderation_menu_keyboard
        await update.message.reply_text("Меню модерирования:", reply_markup=get_moderation_menu_keyboard())
        return MODERATION_MENU
    else:
        await update.message.reply_text("🚫 У вас недостаточно прав для доступа к модерационному меню.")
        return MAIN_MENU


async def handle_moderation_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Создать мероприятие":
        return await moderator_create_event_start(update, context)
    elif text == "Просмотреть мероприятия":
        return await moderator_view_events(update, context)
    elif text == "Удалить мероприятие":
        return await moderator_delete_event(update, context)
    elif text == "Найти пользователей":
        return await moderator_search_event_users(update, context)
    elif text == "Список мероприятий":
        return await moderator_list_all_events(update, context)
    elif text == "Вернуться в главное меню":
        from bot.keyboards import get_main_menu_keyboard
        user_record = db.get_user(update.effective_user.id)
        role = user_record.get("role") if user_record else "user"
        await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=get_main_menu_keyboard(role=role))
        return MAIN_MENU
    else:
        await update.message.reply_text("Неизвестная команда в меню модерации. Попробуйте снова.")

    from bot.keyboards import get_moderation_menu_keyboard
    await update.message.reply_text("Меню модерации:", reply_markup=get_moderation_menu_keyboard())
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
    await update.message.reply_text("Введите город проведения мероприятия:")
    return MODERATOR_EVENT_CITY

async def moderator_handle_event_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_city"] = update.message.text.strip()
    await update.message.reply_text("Введите описание мероприятия:")
    return MODERATOR_EVENT_DESCRIPTION

async def moderator_handle_event_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["event_description"] = update.message.text.strip()
    summary = (
        f"Название: {context.user_data['event_name']}\n"
        f"Дата: {context.user_data['event_date']}\n"
        f"Время: {context.user_data['event_time']}\n"
        f"Город: {context.user_data['event_city']}\n"
        f"Описание: {context.user_data['event_description']}\n\n"
        "Подтверждаете создание мероприятия? (Да/Нет)"
    )
    await update.message.reply_text(summary)
    return MODERATOR_EVENT_CONFIRMATION

async def moderator_confirm_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    response = update.message.text.strip().lower()
    if response not in ["да", "yes"]:
        await update.message.reply_text("Создание мероприятия отменено.")
        return MAIN_MENU
    user = update.effective_user
    event_name = context.user_data.get("event_name")
    event_date = context.user_data.get("event_date")
    event_time = context.user_data.get("event_time")
    event_city = context.user_data.get("event_city")
    event_description = context.user_data.get("event_description")
    # Сохраняем идентификатор модератора в поле creator
    creator = f"moderator:{user.id}"
    tags = f"Название: {event_name}; Описание: {event_description}"
    try:
        db.add_event_detail(
            project_id=None,
            event_date=event_date,
            start_time=event_time,
            city=event_city,
            creator=creator,
            participants_count=0,
            participation_points=5,
            tags=tags
        )
        await update.message.reply_text("Мероприятие успешно создано!")
    except Exception as e:
        logger.error(f"Ошибка при создании мероприятия: {e}")
        await update.message.reply_text(f"Ошибка при создании мероприятия: {e}")
    # Очищаем временные данные
    for key in ["event_name", "event_date", "event_time", "event_city", "event_description"]:
        context.user_data.pop(key, None)
    return MODERATION_MENU

# Просмотр пользователей, зарегистрированных на мероприятие модератора
async def moderator_view_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список мероприятий, созданных модератором, с кнопками для просмотра зарегистрированных пользователей."""
    user = update.effective_user
    creator_str = f"moderator:{user.id}"
    events = [event for event in db.get_all_events() if event.get("creator") == creator_str]
    if not events:
        await update.message.reply_text("У вас нет созданных мероприятий.")
        return MODERATION_MENU
    keyboard = []
    for event in events:
        # Из тегов извлекаем название мероприятия
        name = event.get("tags", "").split(";")[0].replace("Название:", "").strip()
        button_text = f"{name} ({event.get('event_date')})"
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
    return MAIN_MENU

# Удаление мероприятия модератором
async def moderator_delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список мероприятий модератора с кнопками для удаления."""
    user = update.effective_user
    creator_str = f"moderator:{user.id}"
    events = [event for event in db.get_all_events() if event.get("creator") == creator_str]
    if not events:
        await update.message.reply_text("У вас нет созданных мероприятий для удаления.")
        return MAIN_MENU
    keyboard = []
    for event in events:
        name = event.get("tags", "").split(";")[0].replace("Название:", "").strip()
        button_text = f"{name} ({event.get('event_date')})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"delete_event:{event['id']}")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Выберите мероприятие для удаления:", reply_markup=reply_markup)
    return MAIN_MENU

async def moderator_handle_delete_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие кнопки удаления мероприятия."""
    query = update.callback_query
    await query.answer()
    event_id = query.data.split(":", 1)[1]
    user = update.effective_user
    event = db.get_event_by_id(int(event_id))
    if event and event.get("creator") == f"moderator:{user.id}":
        try:
            db.delete_event(event_id)
            await query.edit_message_text("Мероприятие успешно удалено.")
        except Exception as e:
            await query.edit_message_text(f"Ошибка при удалении мероприятия: {e}")
    else:
        await query.edit_message_text("🚫 Это мероприятие не принадлежит вам.")
    return MAIN_MENU

async def moderator_handle_search_event_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_id_text = update.message.text.strip()
    try:
        event_id = int(event_id_text)
    except ValueError:
        await update.message.reply_text("Неверный формат ID мероприятия. Введите числовое значение.")
        return MODERATOR_SEARCH_REGISTERED_USERS

    users = db.get_users_for_event(event_id)
    if not users:
        await update.message.reply_text("На данном мероприятии нет зарегистрированных пользователей.")
    else:
        message = "Зарегистрированные пользователи:\n"
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
        name = ""
        if event.get("tags"):
            parts = event["tags"].split(";")
            for part in parts:
                if "Название:" in part:
                    name = part.split("Название:")[1].strip()
                    break
        if not name:
            name = f"Мероприятие #{event['id']}"
        message_lines.append(f"{event['id']}: {name}")

    message_text = "\n".join(message_lines)
    await update.message.reply_text(message_text)
    return MODERATION_MENU
