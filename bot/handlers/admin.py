"""Обработчики админских команд."""

import os
import csv
import openpyxl
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from bot.states import MAIN_MENU, WAIT_FOR_CSV, WAIT_FOR_EVENTS_CSV
from database.db import Database
import logging

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
                location = row.get("Локация", "")
                creator = row.get("Организатор", "")
                description = row.get("Описание", "")
                
                # Получаем стоимость (ценность) мероприятия
                try:
                    participation_points = int(row.get("Ценность", "100").strip())
                except (ValueError, TypeError):
                    participation_points = 100  # Значение по умолчанию
                
                if not name or not event_date or not start_time or not location or not creator:
                    continue
                
                # TODO: Заполнение тегов будет реализовано через AI агента
                # Теги будут выбираться из списка констант в bot/constants.py
                # Временно сохраняем базовую информацию о мероприятии
                tags = f"Название: {name}; Локация: {location}; Описание: {description}"
                
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
                        location=location
                    )
                    count += 1
                except Exception as e:
                    logger.error(f"Ошибка при добавлении мероприятия: {e}")
                    
        os.remove(temp_path)
        await update.message.reply_markdown(f"*✅ CSV файл обработан успешно.* Добавлено мероприятий: _{count}_.")
    except Exception as e:
        logger.error(f"Ошибка при обработке CSV файла с мероприятиями: {e}")
        await update.message.reply_markdown("*🚫 Произошла ошибка при обработке CSV файла с мероприятиями.*")
    return MAIN_MENU
