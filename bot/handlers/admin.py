"""Обработчики админских команд."""

import os
import csv
import logging
from config         import ADMIN_ID
from database       import UserModel, EventModel
from database.connection import get_db_connection
from datetime       import datetime
from functools      import wraps
from bot.constants  import CITIES, TAGS
from telegram       import ReplyKeyboardRemove, Update, ReplyKeyboardMarkup
from telegram.ext   import ContextTypes
from database.models.project import ProjectModel

from bot.keyboards  import (get_admin_menu_keyboard, get_mod_menu_keyboard, get_city_selection_keyboard, get_tag_selection_keyboard,
                           get_cancel_keyboard, get_city_selection_keyboard_with_cancel, get_tag_selection_keyboard_with_cancel,
                           get_confirm_keyboard, get_csv_export_menu_keyboard)
from bot.states     import (ADMIN_MENU, MAIN_MENU, MOD_EVENT_DELETE, MOD_EVENT_USERS, ADMIN_SET_ADMIN, EVENT_CSV_IMPORT,
                            ADMIN_DELETE_USER, EVENT_CSV_UPLOAD, MOD_MENU, MOD_EVENT_NAME,
                            MOD_EVENT_DATE, MOD_EVENT_TIME, MOD_EVENT_CITY, MOD_EVENT_DESCRIPTION,
                            MOD_EVENT_CONFIRM, MOD_EVENT_POINTS, MOD_EVENT_TAGS,
                            MOD_EVENT_CREATOR, MOD_EVENT_CODE, ADMIN_FIND_USER_ID, ADMIN_FIND_USER_NAME,
                            ADMIN_SET_MODERATOR, CSV_EXPORT_MENU, EVENT_REPORT_CREATE, EVENT_REPORT_PARTICIPANTS,
                            EVENT_REPORT_PHOTOS, EVENT_REPORT_SUMMARY, EVENT_REPORT_FEEDBACK, MOD_EVENT_EDIT_SELECT,
                            MOD_EVENT_EDIT_FIELD, MOD_EVENT_EDIT_VALUE, MOD_EVENT_PROJECT, PROJECTS_CSV_UPLOAD,
                            ADMIN_PROJECT_EXPORT)


logger = logging.getLogger(__name__)

user_db = UserModel()
event_db = EventModel()

def role_required(*allowed_roles):
    """
    Декоратор для проверки роли пользователя.
    Разрешает доступ только пользователям с указанными ролями.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            user = update.effective_user
            user_record = user_db.get_user(user.id)
            user_role = user_record.get("role") if user_record else None
            
            if not user_role or user_role not in allowed_roles:
                await update.message.reply_markdown("*🚫 У вас нет доступа к этой команде\\.*")
                return MAIN_MENU
                
            return await func(update, context)
        return wrapper
    return decorator

@role_required("admin")
async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /admin."""
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
        "• `/search_events_tag <tag>` \\- поиск мероприятий по тегу\n"
        "• `/load_events_csv` \\- загрузить CSV с мероприятиями"
    )

@role_required("admin")
async def set_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /set_admin."""
    try:
        target_user_id = int(context.args[0])
        user_db.update_user_role(target_user_id, "admin")
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} назначен администратором.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /set_admin <user_id>*")

@role_required("admin")
async def unset_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /unset_admin."""
    try:
        target_user_id = int(context.args[0])
        user_db.update_user_role(target_user_id, "user")
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} удален из администраторов.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /unset_admin <user_id>*")

@role_required("admin")
async def set_moderator(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /set_moderator."""
    try:
        target_user_id = int(context.args[0])
        user_db.update_user_role(target_user_id, "moderator")
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} назначен модератором.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /set_moderator <user_id>*")

@role_required("admin", "moderator")
async def delete_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /delete_user."""
    try:
        target_user_id = int(context.args[0])
        if target_user_id in ADMIN_ID:
            await update.message.reply_markdown("*🚫 Вы не можете удалить администратора.*")
            return
        user_db.delete_user(target_user_id)
        await update.message.reply_markdown(f"*✅ Пользователь {target_user_id} удален.*")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /delete_user <user_id>*")

@role_required("admin", "moderator")
async def find_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_user_id."""
    try:
        target_user_id = int(context.args[0])
        user = user_db.find_user_by_id(target_user_id)
        if user is None:
            await update.message.reply_markdown("*❌ Пользователь не найден.*")
        else:
            await update.message.reply_markdown(f"*👤 Пользователь найден:*\n{user}")
    except (IndexError, ValueError):
        await update.message.reply_markdown("*⚠️ Использование: /find_user_id <user_id>*")

@role_required("admin", "moderator")
async def find_users_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /find_users_name."""
    try:
        name = " ".join(context.args)
        users = user_db.find_users_by_name(name)
        if not users:
            await update.message.reply_markdown("*❌ Пользователи не найдены.*")
        else:
            message = "*👥 Найденные пользователи:*\n"
            for user in users:
                message += f"ID: {user['id']}, Имя: {user['first_name']} {user['last_name']}\n"
            await update.message.reply_markdown(message)
    except Exception:
        await update.message.reply_markdown("*🚫 Ошибка при поиске пользователей по имени.*")

@role_required("admin")
async def load_events_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /load_events_csv."""
    await update.message.reply_markdown("*📥 Пожалуйста, отправьте CSV файл с данными о мероприятиях (расширение .csv).*")
    return EVENT_CSV_UPLOAD

@role_required("admin")
async def process_events_csv_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик загрузки CSV файла с мероприятиями согласно новой схеме БД."""
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        data_folder = os.path.join(".", "data")
        os.makedirs(data_folder, exist_ok=True)
        temp_path = os.path.join(data_folder, update.message.document.file_name)
        await file.download_to_drive(custom_path=temp_path)
        count = 0
        await update.message.reply_markdown("*📥 Старт обработки CSV файла с мероприятиями...*")

        with open(temp_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get("Название", "").strip()
                event_date = row.get("Дата", "").strip()
                start_time = row.get("Время", "").strip()
                city = row.get("Локация", "").strip()
                creator = row.get("Организатор", "").strip()
                description = row.get("Описание", "").strip()
                participation_points = 5
                tags = row.get("Теги", "").strip()
                code = row.get("Код", "").strip()
                owner = "admin"
                project_id = None

                try:
                    event_db.add_event(
                        name=name,
                        event_date=event_date,
                        start_time=start_time,
                        city=city,
                        creator=creator,
                        description=description,
                        participation_points=participation_points,
                        tags=tags,
                        code=code,
                        owner=owner,
                        project_id=project_id
                    )
                    count += 1
                    await update.message.reply_markdown(f"*✅ Мероприятие '{name}' успешно добавлено.*")
                except Exception as e:
                    logger.error(f"Ошибка при добавлении мероприятия '{name}': {e}")

        os.remove(temp_path)
        await update.message.reply_markdown(f"*✅ CSV обработан успешно.* Добавлено мероприятий: _{count}_.")
    except Exception as e:
        logger.error(f"Ошибка при обработке CSV файла с мероприятиями: {e}")
        await update.message.reply_markdown("*🚫 Ошибка при обработке CSV файла с мероприятиями.*")
    return MAIN_MENU


@role_required("admin")
async def process_projects_csv_document(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик загрузки CSV файла с проектами.
    Ожидается, что CSV содержит столбцы "Название", "Описание" и "Ответственный".
    """
    import csv
    try:
        file = await context.bot.get_file(update.message.document.file_id)
        data_folder = os.path.join(".", "data")
        if not os.path.exists(data_folder):
            os.makedirs(data_folder)
        temp_path = os.path.join(data_folder, update.message.document.file_name)
        await file.download_to_drive(custom_path=temp_path)
        count = 0
        await update.message.reply_markdown("*📥 Обрабатываем CSV файл с проектами...*")

        from database.models.project import ProjectModel
        project_db = ProjectModel()

        with open(temp_path, newline="", encoding="utf-8") as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                name = row.get("Проект", "").strip()
                description = row.get("Описание", "").strip()
                responsible = row.get("Ответственный", "").strip()
                if not name:
                    continue
                try:
                    project_db.add_project(name, description, responsible)
                    count += 1
                    await update.message.reply_markdown(f"*✅ Проект {name} добавлен в базу данных.*")
                except Exception as e:
                    if "UNIQUE constraint failed" in str(e):
                        await update.message.reply_markdown(f"*⚠️ Проект {name} уже существует.*")
                    else:
                        logger.error(f"Ошибка при добавлении проекта: {e}")
        os.remove(temp_path)
        await update.message.reply_markdown(f"*✅ CSV файл обработан успешно.* Добавлено проектов: _{count}_.")
    except Exception as e:
        logger.error(f"Ошибка при обработке CSV файла с проектами: {e}")
        await update.message.reply_markdown("*🚫 Произошла ошибка при обработке CSV файла с проектами.*")
    return ADMIN_MENU

@role_required("admin", "moderator")
async def admin_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Меню администратора:", reply_markup=get_admin_menu_keyboard())
    return ADMIN_MENU

async def handle_admin_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Установить админа":
        await update.message.reply_text("Введите ID пользователя для установки в роли администратора:")
        return ADMIN_SET_ADMIN
    elif text == "Установить модератора":
        await update.message.reply_text("Введите ID пользователя для установки в роли модератора:")
        return ADMIN_SET_MODERATOR
    elif text == "Удалить пользователя":
        await update.message.reply_text("Введите ID пользователя для удаления:")
        return ADMIN_DELETE_USER
    elif text == "Найти пользователя по ID":
        await update.message.reply_text("Введите ID пользователя для поиска:")
        return ADMIN_FIND_USER_ID
    elif text == "Найти пользователя по имени":
        await update.message.reply_text("Введите имя пользователя для поиска:")
        return ADMIN_FIND_USER_NAME
    elif text == "Загрузить мероприятия из CSV":
        await update.message.reply_text("Отправьте CSV файл с мероприятиями:")
        return EVENT_CSV_UPLOAD
    elif text == "Загрузить проекты из CSV":
        await update.message.reply_text("Отправьте CSV файл с проектами:")
        return PROJECTS_CSV_UPLOAD
    elif text == "Выгрузить мероприятия по проекту":
        return await export_events_by_project_csv(update, context)
    elif text == "Вернуться в главное меню":
        from bot.keyboards import get_main_menu_keyboard
        user_record = user_db.get_user(update.effective_user.id)
        role = user_record.get("role") if user_record else "user"
        await update.message.reply_text(
            "Возвращаемся в главное меню.",
            reply_markup=get_main_menu_keyboard(role=role)
        )
        return MAIN_MENU
    else:
        await update.message.reply_text("Неизвестная команда. Выберите действие из меню.")
        return ADMIN_MENU


async def handle_admin_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text
    user = user_db.get_user(user_id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return ADMIN_MENU
    if user.get("role") == "admin":
        await update.message.reply_text("Пользователь уже является администратором.")
        return ADMIN_MENU
    user_db.update_user_role(user_id, "admin")
    await update.message.reply_text("Пользователь успешно назначен администратором.")
    return ADMIN_MENU

async def handle_moderator_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text
    user = user_db.get_user(user_id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return ADMIN_MENU
    if user.get("role") == "admin":
        await update.message.reply_text("Пользователь является администратором. Удалите его из администраторов, чтобы назначить модератором.")
        return ADMIN_MENU
    if user.get("role") == "moderator":
        await update.message.reply_text("Пользователь уже является модератором.")
        return ADMIN_MENU
    user_db.update_user_role(user_id, "moderator")
    await update.message.reply_text("Пользователь успешно назначен модератором.")
    return ADMIN_MENU

async def handle_delete_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text
    user = user_db.get_user(user_id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return ADMIN_MENU
    user_db.delete_user(user_id)
    await update.message.reply_text("Пользователь успешно удален.")
    return ADMIN_MENU

async def handle_find_user_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.text
    user = user_db.get_user(user_id)
    if not user:
        await update.message.reply_text("Пользователь не найден.")
        return ADMIN_MENU
    await update.message.reply_text(f"Пользователь найден: {user}")
    return ADMIN_MENU

async def handle_find_user_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.message.text
    users = user_db.find_users_by_name(user_name)
    if users:
        await update.message.reply_text(f"Найдены пользователи: {users}")
    else:
        await update.message.reply_text("Пользователи не найдены.")
    return ADMIN_MENU

async def handle_events_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик загрузки CSV файла с мероприятиями."""
    if not update.message.document:
        await update.message.reply_text("Пожалуйста, отправьте CSV файл с мероприятиями.")
        return EVENT_CSV_UPLOAD

    if not update.message.document.file_name.endswith('.csv'):
        await update.message.reply_text("Пожалуйста, отправьте файл с расширением .csv")
        return EVENT_CSV_UPLOAD

    try:
        # Используем существующую функцию для обработки CSV
        return await process_events_csv_document(update, context)
    except Exception as e:
        logger.error(f"Ошибка при обработке CSV файла: {e}")
        await update.message.reply_text("Произошла ошибка при обработке файла. Пожалуйста, проверьте формат и попробуйте снова.")
        return ADMIN_MENU

@role_required("admin", "moderator")
async def moderation_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Меню модерирования:", reply_markup=get_mod_menu_keyboard())
    return MOD_MENU

async def handle_moderation_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Создать мероприятие":
        await update.message.reply_text("✨ Введите название мероприятия:", reply_markup=get_cancel_keyboard())
        return MOD_EVENT_NAME

    elif text == "Редактировать мероприятие":
        await update.message.reply_text("Введите ID мероприятия для редактирования:", reply_markup=get_cancel_keyboard())
        return MOD_EVENT_EDIT_SELECT

    elif text == "Удалить мероприятие":
        return await moderator_delete_event(update, context)

    elif text == "Мои мероприятия":
        return await moderator_view_events(update, context)

    elif text == "Удалить мероприятие":
        return await moderator_delete_event(update, context)

    elif text == "Посмотреть участников":
        await update.message.reply_text("Введите ID мероприятия для поиска зарегистрированных пользователей:")
        return MOD_EVENT_USERS

    elif text == "Все мероприятия":
        return await moderator_list_all_events(update, context)

    elif text == "Выгрузить CSV":
        await update.message.reply_text("Выберите вариант экспорта:", reply_markup=get_csv_export_menu_keyboard())
        return CSV_EXPORT_MENU

    elif text == "Создать отчет":
        return await create_event_report(update, context)

    elif text == "Просмотреть отчет":
        return await view_event_report(update, context)

    elif text == "Все проекты":
        project_db = ProjectModel()
        projects = project_db.get_all_projects()
        if not projects:
            await update.message.reply_text("Нет проектов.", reply_markup=get_mod_menu_keyboard())
            return MOD_MENU

        message = "📋 Список проектов:\n\n"
        for project in projects:
            message += f"• *{project['name']}*\n"
            if project.get('description'):
                message += f"  📝 {project['description']}\n"
            if project.get('responsible'):
                message += f"  👤 Ответственный: {project['responsible']}\n"
            message += "\n"

        await update.message.reply_markdown_v2(escape_markdown_v2(message), reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    elif text == "Вернуться в главное меню":
        from bot.keyboards import get_main_menu_keyboard
        user_record = user_db.get_user(update.effective_user.id)
        role = user_record.get("role") if user_record else "user"
        await update.message.reply_text(
            "Возвращаемся в главное меню.",
            reply_markup=get_main_menu_keyboard(role=role)
        )
        return MAIN_MENU

    else:
        await update.message.reply_text("Неизвестная команда. Выберите действие из меню.",
                                        reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

@role_required("admin", "moderator")
async def moderator_create_event_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("✨ Введите название мероприятия:", reply_markup=get_cancel_keyboard())
    return MOD_EVENT_NAME

async def handle_event_creation_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик отмены создания мероприятия"""
    await update.message.reply_text(
        "❌ Создание мероприятия отменено.",
        reply_markup=get_mod_menu_keyboard()
    )
    return MOD_MENU

async def moderator_handle_event_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)
    context.user_data["event_name"] = text
    await update.message.reply_text("📅 Введите дату мероприятия (ДД.ММ.ГГГГ):", reply_markup=get_cancel_keyboard())
    return MOD_EVENT_DATE

async def moderator_handle_event_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)

    try:
        datetime.strptime(text, "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат даты. Пожалуйста, используйте формат ДД.ММ.ГГГГ.", 
                                      reply_markup=get_cancel_keyboard())
        return MOD_EVENT_DATE
    
    context.user_data["event_date"] = text
    await update.message.reply_text("⏰ Введите время мероприятия (ЧЧ:ММ):", reply_markup=get_cancel_keyboard())
    return MOD_EVENT_TIME

async def moderator_handle_event_time(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)

    try:
        datetime.strptime(text, "%H:%M")
    except ValueError:
        await update.message.reply_text("❌ Неверный формат времени. Пожалуйста, используйте формат ЧЧ:ММ.", 
                                      reply_markup=get_cancel_keyboard())
        return MOD_EVENT_TIME

    context.user_data["event_time"] = text
    await update.message.reply_text(
        "📍 Выберите территорию проведения мероприятия:",
        reply_markup=get_city_selection_keyboard_with_cancel()
    )
    return MOD_EVENT_CITY

async def moderator_handle_event_city(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)

    if text not in CITIES:
        await update.message.reply_text(
            "❌ Выбранная территория недоступна. Пожалуйста, выберите из предложенных ниже:",
            reply_markup=get_city_selection_keyboard_with_cancel()
        )
        return MOD_EVENT_CITY

    context.user_data["event_city"] = text
    await update.message.reply_text("👤 Введите организатора мероприятия:", reply_markup=get_cancel_keyboard())
    return MOD_EVENT_CREATOR

async def moderator_handle_event_creator(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)
    context.user_data["event_creator"] = text
    await update.message.reply_text(
        "💰 Количество баллов за участие: 5. Напишите любое сообщение для продолжение.",
        reply_markup=get_cancel_keyboard()
    )
    return MOD_EVENT_POINTS

async def moderator_handle_event_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)
    context.user_data["event_description"] = text
    await update.message.reply_text(
        "Введите название проекта для мероприятия (если проект не нужен, введите 'Отмена' или оставьте поле пустым):",
        reply_markup=get_cancel_keyboard()
    )
    return MOD_EVENT_PROJECT

async def moderator_handle_event_project(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    project_id = update.message.text.strip()
    if project_id in ["❌ Отмена", "Отмена", ""]:
        context.user_data["project_id"] = None
    else:
        project_db = ProjectModel()
        project = project_db.get_project_by_id(int(project_id))
        if project:
            context.user_data["project_id"] = project["id"]
        else:
            await update.message.reply_text(
                "Проект с таким названием не найден. Если хотите создать мероприятие без проекта, нажмите '❌ Отмена'.:",
                reply_markup=get_cancel_keyboard()
            )
            return MOD_EVENT_PROJECT
    await update.message.reply_text(
        "Введите теги мероприятия:",
        reply_markup=get_tag_selection_keyboard_with_cancel()
    )
    return MOD_EVENT_TAGS

async def moderator_handle_event_participation_points(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text:
        context.user_data["event_participation_points"] = 5
    else:
        try:
            points = int(text)
            context.user_data["event_participation_points"] = points
        except ValueError:
            await update.message.reply_text(
                "❌ Пожалуйста, введите числовое значение для баллов, или '❌ Отмена' для значения по умолчанию.",
                reply_markup=get_cancel_keyboard()
            )
            return MOD_EVENT_POINTS
    await update.message.reply_text(
        "📝 Введите описание мероприятия:",
        reply_markup=get_cancel_keyboard()
    )
    return MOD_EVENT_DESCRIPTION


async def moderator_handle_event_tags(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)
        
    if text == "✅ Готово":
        if not context.user_data.get("selected_tags"):
            await update.message.reply_text(
                "❌ Необходимо выбрать хотя бы один тег. Выберите теги мероприятия:",
                reply_markup=get_tag_selection_keyboard_with_cancel(selected_tags=context.user_data.get("selected_tags", []))
            )
            return MOD_EVENT_TAGS
            
        # Сохраняем выбранные теги и переходим к следующему шагу
        context.user_data["event_tags"] = ",".join(context.user_data.get("selected_tags", []))
        await update.message.reply_text(
            "🔑 Введите код для мероприятия (один для всех пользователей):",
            reply_markup=get_cancel_keyboard()
        )
        return MOD_EVENT_CODE

    selected_tag = text.split(" ✔️")[0]
    if selected_tag in TAGS:
        selected_tags = context.user_data.get("selected_tags", [])
        if selected_tag in selected_tags:
            selected_tags.remove(selected_tag)
        else:
            selected_tags.append(selected_tag)
        context.user_data["selected_tags"] = selected_tags
        
        await update.message.reply_text(
            "🏷️ Выберите теги мероприятия (можно выбрать несколько):",
            reply_markup=get_tag_selection_keyboard_with_cancel(selected_tags=selected_tags)
        )
        return MOD_EVENT_TAGS
        
    await update.message.reply_text(
        "❌ Пожалуйста, выберите теги из предложенных вариантов.",
        reply_markup=get_tag_selection_keyboard_with_cancel(selected_tags=context.user_data.get("selected_tags", []))
    )
    return MOD_EVENT_TAGS

async def moderator_handle_event_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await handle_event_creation_cancel(update, context)

    context.user_data["event_code"] = text
    summary = (
        f"📋 *Проверьте данные мероприятия:*\n\n"
        f"📌 *Название:* {context.user_data['event_name']}\n"
        f"📅 *Дата:* {context.user_data['event_date']}\n"
        f"⏰ *Время:* {context.user_data['event_time']}\n"
        f"📍 *Локация:* {context.user_data['event_city']}\n"
        f"👤 *Организатор:* {context.user_data['event_creator']}\n"
        f"🚀 *Проект:* {context.user_data['project_id']}\n"
        f"📝 *Описание:* {context.user_data['event_description']}\n"
        f"💰 *Ценность:* {context.user_data['event_participation_points']}\n"
        f"🏷️ *Теги:* {context.user_data['event_tags']}\n"
        f"🔑 *Код:* {context.user_data['event_code']}\n\n"
        "Подтверждаете создание мероприятия?"
    )
    await update.message.reply_markdown(summary, reply_markup=get_confirm_keyboard())
    return MOD_EVENT_CONFIRM

async def moderator_confirm_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    
    if text == "❌ Нет":
        return await handle_event_creation_cancel(update, context)
        
    if text != "✅ Да":
        await update.message.reply_text(
            "Пожалуйста, выберите '✅ Да' для подтверждения или '❌ Нет' для отмены.",
            reply_markup=get_confirm_keyboard()
        )
        return MOD_EVENT_CONFIRM
        
    try:
        owner = f"moderator:{update.effective_user.id}"

        event_db.add_event(
            name=context.user_data["event_name"],
            event_date=context.user_data["event_date"],
            start_time=context.user_data["event_time"],
            city=context.user_data["event_city"],
            creator=context.user_data["event_creator"],
            description=context.user_data["event_description"],
            participation_points=context.user_data["event_participation_points"],
            tags=context.user_data["event_tags"],
            code=context.user_data["event_code"],
            owner=owner,
            project_id=context.user_data.get("project_id")  # Добавляем привязку к проекту
        )
        
        await update.message.reply_text(
            "✅ Мероприятие успешно создано!", 
            reply_markup=get_mod_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при создании мероприятия: {e}")
        await update.message.reply_text(
            f"❌ Ошибка при создании мероприятия: {e}", 
            reply_markup=get_mod_menu_keyboard()
        )
    
    return MOD_MENU

# Просмотр пользователей, зарегистрированных на мероприятие модератора
@role_required("admin", "moderator")
async def moderator_view_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список мероприятий, созданных модератором."""
    user = update.effective_user
    user_record = user_db.get_user(user.id)

    # Для админа показываем все мероприятия, для модератора - только его
    if user_record.get("role") == "admin":
        events = event_db.get_all_events()
    else:
        owner_str = f"moderator:{user.id}"
        events = [event for event in event_db.get_all_events() if event.get("owner") == owner_str]

    if not events:
        await update.message.reply_text("Нет доступных мероприятий.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    message = "Список созданных вами мероприятий и зарегистрированных на них пользователей:\n\n"
    for event in events:
        users = event_db.get_users_for_event(event['id'])
        message += f"📌 {event['name']}\n"
        message += f"📅 {event['event_date']}\n"
        message += f"⏰ {event['start_time']}\n"
        message += f"📍 {event['city']}\n"
        message += f"🔑 Код: {event.get('code')}\n"
        if users:
            message += "Зарегистрированные пользователи:\n"
            for u in users:
                message += f"- {u['first_name']} (ID: {u['id']})\n"
        else:
            message += "Нет зарегистрированных пользователей\n"
        message += "\n"

    await update.message.reply_text(message, reply_markup=get_mod_menu_keyboard())
    return MOD_MENU

async def moderator_handle_view_event_users_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие кнопки просмотра зарегистрированных пользователей."""
    query = update.callback_query
    await query.answer()
    event_id = query.data.split(":", 1)[1]
    users = event_db.get_users_for_event(event_id)
    if not users:
        await query.edit_message_text("На данном мероприятии нет зарегистрированных пользователей.")
    else:
        message = "Зарегистрированные пользователи:\n"
        for u in users:
            message += f"ID: {u['id']}, Имя: {u['first_name']}\n"
        await query.edit_message_text(message)
    return MOD_MENU

@role_required("admin", "moderator")
async def moderator_delete_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выводит список мероприятий для удаления."""
    user = update.effective_user
    user_record = user_db.get_user(user.id)

    # Для админа показываем все мероприятия, для модератора - только его
    if user_record.get("role") == "admin":
        events = event_db.get_all_events()
    else:
        owner_str = f"moderator:{user.id}"
        events = [event for event in event_db.get_all_events() if event.get("owner") == owner_str]

    if not events:
        await update.message.reply_text("Нет доступных мероприятий для удаления.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    message = "Список мероприятий для удаления:\n\n"
    for event in events:
        message += f"ID: {event['id']} - {event['name']} ({event.get('event_date')})\n"
    
    message += "\nДля удаления мероприятия введите его ID:"
    await update.message.reply_text(message)
    return MOD_EVENT_DELETE

@role_required("admin", "moderator")
async def moderator_handle_delete_event_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает нажатие кнопки удаления мероприятия."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID мероприятия из callback_data
    event_id = int(query.data.split(":", 1)[1])
    
    user = update.effective_user

    # Получаем информацию о мероприятии
    event = event_db.get_event_by_id(event_id)
    if not event:
        await query.edit_message_text("❌ Мероприятие не найдено.")
        return MOD_MENU

    # Проверяем, может ли модератор удалить это мероприятие
    if event.get("owner") != f"moderator:{user.id}":
        await query.edit_message_text("🚫 Вы можете удалять только свои мероприятия.")
        return MOD_MENU

    try:
        # Удаляем мероприятие
        event_db.delete_event(event_id)
        await query.edit_message_text(f"✅ Мероприятие \"{event.get('name')}\" успешно удалено.")
    except Exception as e:
        logger.error(f"Ошибка при удалении мероприятия: {e}")
        await query.edit_message_text("❌ Произошла ошибка при удалении мероприятия.")
    
    return MOD_MENU

async def moderator_handle_search_event_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_id_text = update.message.text.strip()
    try:
        event_id = int(event_id_text)
    except ValueError:
        await update.message.reply_text("Неверный формат ID мероприятия. Введите числовое значение.")
        return MOD_EVENT_USERS

    # Получаем информацию о мероприятии по его ID
    event = event_db.get_event_by_id(event_id)
    if not event:
        await update.message.reply_text("Мероприятие не найдено.")
        return MOD_MENU

    # Извлекаем название и код мероприятия из поля tags
    name = event.get("name")
    code = event.get("code")

    # Формируем заголовок с названием и кодом мероприятия
    message = f"Мероприятие: {name}"
    message += f" (Код: {code})"
    message += "\n\nЗарегистрированные пользователи:\n"

    # Получаем пользователей, зарегистрированных на мероприятие
    users = event_db.get_users_for_event(event_id)
    if not users:
        message += "Нет зарегистрированных пользователей."
    else:
        for u in users:
            message += f"ID: {u['id']}, Имя: {u['first_name']}\n"
    await update.message.reply_text(message)
    return MOD_MENU

async def moderator_search_event_users(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Введите ID мероприятия для поиска зарегистрированных пользователей:")
    return MOD_EVENT_USERS

async def moderator_list_all_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    events = event_db.get_all_events()
    if not events:
        await update.message.reply_text("📭 Нет доступных мероприятий.")
        return MOD_MENU

    message_lines = ["📋 Список всех мероприятий:\n"]
    for event in events:
        id = event.get("id")
        name = event.get("name")
        date = event.get("date", "Дата не указана")
        start_time = event.get("start_time", "Время не указано")
        city = event.get("city", "Регион не указан")

        message_lines.append(f"📌 {name}")
        message_lines.append(f"📅 Дата: {date}")
        message_lines.append(f"⏰ Время: {start_time}")
        message_lines.append(f"📍 Регион: {city}\n")

    message_text = "\n".join(message_lines)
    await update.message.reply_text(message_text)
    return MOD_MENU

async def handle_event_delete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод ID мероприятия для удаления."""
    try:
        event_id = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("Неверный формат ID. Введите числовое значение.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    # Проверяем права пользователя
    user = update.effective_user
    user_record = user_db.get_user(user.id)
    if not user_record or user_record.get("role") not in ["admin", "moderator"]:
        await update.message.reply_text("🚫 У вас нет прав на удаление мероприятий.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    # Получаем информацию о мероприятии
    event = event_db.get_event_by_id(event_id)
    if not event:
        await update.message.reply_text("❌ Мероприятие не найдено.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    # Проверяем, может ли модератор удалить это мероприятие
    if user_record.get("role") == "moderator" and event.get("owner") != f"moderator:{user.id}":
        await update.message.reply_text("🚫 Вы можете удалять только свои мероприятия.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    try:
        # Удаляем мероприятие
        event_db.delete_event(event_id)
        await update.message.reply_text(f"✅ Мероприятие \"{event.get('name')}\" успешно удалено.", reply_markup=get_mod_menu_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при удалении мероприятия: {e}")
        await update.message.reply_text("❌ Произошла ошибка при удалении мероприятия.", reply_markup=get_mod_menu_keyboard())
    
    return MOD_MENU


async def moderator_export_events_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        events = event_db.get_all_events()
        if not events:
            await update.message.reply_text("Нет мероприятий для экспорта.", reply_markup=get_mod_menu_keyboard())
            return MOD_MENU

        # Создаем временный файл в папке data
        os.makedirs("data", exist_ok=True)
        temp_file = os.path.join("data", "events_export.csv")

        fieldnames = ["id", "name", "event_date", "start_time", "city", "creator", "description",
                      "participation_points", "participants_count", "tags", "code", "owner", "project_id"]

        with open(temp_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for event in events:
                row = dict(event)
                writer.writerow({
                    "id": row.get("id", ""),
                    "name": row.get("name", ""),
                    "event_date": row.get("event_date", ""),
                    "start_time": row.get("start_time", ""),
                    "city": row.get("city", ""),
                    "creator": row.get("creator", ""),
                    "description": row.get("description", ""),
                    "participation_points": row.get("participation_points", 0),
                    "participants_count": row.get("participants_count", 0),
                    "tags": row.get("tags", ""),
                    "code": row.get("code", ""),
                    "owner": row.get("owner", ""),
                    "project_id": row.get("project_id", "")
                })

        with open(temp_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="events_export.csv",
                caption="Выгрузка мероприятий в CSV формате"
            )

        os.remove(temp_file)
        return MOD_MENU

    except Exception as e:
        logger.error(f"Ошибка при экспорте CSV: {e}")
        await update.message.reply_text("Произошла ошибка при экспорте мероприятий.",
                                        reply_markup=get_mod_menu_keyboard())
        return MOD_MENU


@role_required("admin", "moderator")
async def moderator_export_users_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        # Предполагается, что у модели пользователей есть метод get_all_users()
        users = user_db.get_all_users()
        if not users:
            await update.message.reply_text("Нет данных пользователей для экспорта.",
                                            reply_markup=get_mod_menu_keyboard())
            return MOD_MENU

        os.makedirs("data", exist_ok=True)
        temp_file = os.path.join("data", "users_export.csv")

        fieldnames = ["id", "first_name", "telegram_tag", "employee_number", "role", "score", "registered_events",
                      "tags", "city"]
        with open(temp_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for event in events:
                row = dict(event)  # Преобразуем sqlite3.Row в словарь
                writer.writerow({
                    "id": row.get("id", ""),
                    "name": row.get("name", ""),
                    "event_date": row.get("event_date", ""),
                    "start_time": row.get("start_time", ""),
                    "city": row.get("city", ""),
                    "creator": row.get("creator", ""),
                    "description": row.get("description", ""),
                    "participation_points": row.get("participation_points", 0),
                    "participants_count": row.get("participants_count", 0),
                    "tags": row.get("tags", ""),
                    "code": row.get("code", ""),
                    "owner": row.get("owner", ""),
                    "project_id": row.get("project_id", "")
                })

        with open(temp_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="users_export.csv",
                caption="Выгрузка данных пользователей в CSV формате"
            )

        os.remove(temp_file)
        return MOD_MENU
    except Exception as e:
        logger.error(f"Ошибка при экспорте данных пользователей: {e}")
        await update.message.reply_text("Произошла ошибка при экспорте данных пользователей.",
                                        reply_markup=get_mod_menu_keyboard())
        return MOD_MENU


@role_required("admin", "moderator")
async def create_event_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс создания отчета о мероприятии."""
    event_id = context.user_data.get("selected_event_id")
    if not event_id:
        await update.message.reply_text(
            "❌ Сначала выберите мероприятие для создания отчета.",
            reply_markup=ReplyKeyboardRemove()
        )
        return MOD_MENU

    # Проверяем, не существует ли уже отчет
    from database.models.event_report import EventReportModel
    report_model = EventReportModel()
    existing_report = report_model.get_report(event_id)
    
    if existing_report:
        await update.message.reply_text(
            "❌ Отчет для этого мероприятия уже существует.",
            reply_markup=ReplyKeyboardRemove()
        )
        return MOD_MENU

    await update.message.reply_text(
        "📊 Создание отчета о мероприятии\n\n"
        "Укажите фактическое количество участников:",
        reply_markup=get_cancel_keyboard()
    )
    return EVENT_REPORT_PARTICIPANTS

async def handle_report_participants(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод количества участников."""
    try:
        participants = int(update.message.text)
        if participants < 0:
            raise ValueError("Количество участников не может быть отрицательным")
        context.user_data["report_participants"] = participants
        
        await update.message.reply_text(
            "📸 Отправьте ссылки на фотографии с мероприятия (через запятую):",
            reply_markup=get_cancel_keyboard()
        )
        return EVENT_REPORT_PHOTOS
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректное число участников.",
            reply_markup=get_cancel_keyboard()
        )
        return EVENT_REPORT_PARTICIPANTS

async def handle_report_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод ссылок на фотографии."""
    photos = update.message.text
    context.user_data["report_photos"] = photos
    
    await update.message.reply_text(
        "📝 Введите краткое описание итогов мероприятия:",
        reply_markup=get_cancel_keyboard()
    )
    return EVENT_REPORT_SUMMARY

async def handle_report_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод описания итогов мероприятия."""
    summary = update.message.text
    context.user_data["report_summary"] = summary
    
    await update.message.reply_text(
        "💭 Введите отзывы участников (если есть):\n"
        "Для пропуска этого шага, нажмите 'Пропустить'",
        reply_markup=ReplyKeyboardMarkup([["Пропустить"], ["Отмена"]], resize_keyboard=True)
    )
    return EVENT_REPORT_FEEDBACK

async def handle_report_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод отзывов и создает отчет."""
    feedback = None if update.message.text == "Пропустить" else update.message.text
    
    try:
        from database.models.event_report import EventReportModel
        report_model = EventReportModel()
        
        event_id = context.user_data.get("selected_event_id")
        participants = context.user_data.get("report_participants")
        photos = context.user_data.get("report_photos")
        summary = context.user_data.get("report_summary")
        
        report_model.create_report(
            event_id=event_id,
            actual_participants=participants,
            photos_links=photos,
            summary=summary,
            feedback=feedback
        )
        
        # Очищаем данные отчета
        for key in ["report_participants", "report_photos", "report_summary"]:
            if key in context.user_data:
                del context.user_data[key]
        
        await update.message.reply_text(
            "✅ Отчет о мероприятии успешно создан!",
            reply_markup=get_mod_menu_keyboard()
        )
        return MOD_MENU
        
    except Exception as e:
        logger.error(f"Ошибка при создании отчета: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при создании отчета. Попробуйте позже.",
            reply_markup=get_mod_menu_keyboard()
        )
        return MOD_MENU

@role_required("admin", "moderator")
async def view_event_report(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает отчет о мероприятии."""
    event_id = context.user_data.get("selected_event_id")
    if not event_id:
        await update.message.reply_text(
            "❌ Сначала выберите мероприятие для просмотра отчета.",
            reply_markup=ReplyKeyboardRemove()
        )
        return MOD_MENU

    try:
        from database.models.event_report import EventReportModel
        report_model = EventReportModel()
        report = report_model.get_report(event_id)
        
        if not report:
            await update.message.reply_text(
                "❌ Отчет для этого мероприятия еще не создан.",
                reply_markup=get_mod_menu_keyboard()
            )
            return MOD_MENU
            
        # Получаем информацию о мероприятии
        event = event_db.get_event_by_id(event_id)
        
        report_text = (
            f"📊 *Отчет о мероприятии \"{event['name']}\"*\n\n"
            f"📅 Дата отчета: {report['report_date']}\n"
            f"👥 Фактическое количество участников: {report['actual_participants']}\n\n"
            f"📝 Итоги мероприятия:\n{report['summary']}\n\n"
        )
        
        if report['photos_links']:
            report_text += f"📸 Фотографии: {report['photos_links']}\n\n"
            
        if report['feedback']:
            report_text += f"💭 Отзывы участников:\n{report['feedback']}\n"
            
        await update.message.reply_markdown_v2(
            report_text,
            reply_markup=get_mod_menu_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при просмотре отчета: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при просмотре отчета.",
            reply_markup=get_mod_menu_keyboard()
        )
    
    return MOD_MENU

@role_required("admin", "moderator")
async def handle_csv_export_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text.strip()
    if text == "Выгрузка данных пользователя":
        return await moderator_export_users_csv(update, context)
    elif text == "Выгрузка мероприятий":
        return await moderator_export_events_csv(update, context)
    elif text == "Выгрузка отчётов":
        return await moderator_export_reports_csv(update, context)
    elif text == "Назад":
        # Возвращаемся в основное меню модератора
        await update.message.reply_text("Возвращаемся в меню модератора", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU
    else:
        await update.message.reply_text("Выберите один из вариантов, используя клавиатуру.")
        return CSV_EXPORT_MENU

async def handle_event_report_create(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод ID мероприятия для создания/просмотра отчета."""
    try:
        event_id = int(update.message.text)
        event = event_db.get_event_by_id(event_id)
        
        if not event:
            await update.message.reply_text(
                "❌ Мероприятие с указанным ID не найдено.",
                reply_markup=get_mod_menu_keyboard()
            )
            return MOD_MENU
            
        context.user_data["selected_event_id"] = event_id
        
        # Проверяем, что хочет сделать пользователь: создать или просмотреть отчет
        if context.user_data.get("action") == "view_report":
            return await view_event_report(update, context)
        else:
            return await create_event_report(update, context)
            
    except ValueError:
        await update.message.reply_text(
            "❌ Пожалуйста, введите корректный ID мероприятия (число).",
            reply_markup=get_cancel_keyboard()
        )
        return EVENT_REPORT_CREATE

@role_required("admin", "moderator")
async def moderator_export_reports_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, event_id, report_date, actual_participants, photos_links, summary, feedback FROM event_reports"
        )
        reports = cursor.fetchall()
        conn.close()

        if not reports:
            await update.message.reply_text("Нет отчетов для экспорта.", reply_markup=get_mod_menu_keyboard())
            return MOD_MENU

        os.makedirs("data", exist_ok=True)
        temp_file = os.path.join("data", "reports_export.csv")

        fieldnames = ["id", "event_id", "report_date", "actual_participants", "photos_links", "summary", "feedback"]

        with open(temp_file, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in reports:
                writer.writerow({
                    "id": row["id"],
                    "event_id": row["event_id"],
                    "report_date": row["report_date"],
                    "actual_participants": row["actual_participants"],
                    "photos_links": row["photos_links"],
                    "summary": row["summary"],
                    "feedback": row["feedback"],
                })

        with open(temp_file, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="reports_export.csv",
                caption="Выгрузка отчетов в CSV формате"
            )

        os.remove(temp_file)
        return MOD_MENU

    except Exception as e:
        logger.error(f"Ошибка при экспорте отчетов CSV: {e}")
        await update.message.reply_text(
            "Произошла ошибка при экспорте отчетов.", reply_markup=get_mod_menu_keyboard()
        )
        return MOD_MENU

async def handle_event_edit_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    event_id_str = update.message.text.strip()
    if event_id_str in ["❌ Отмена", "Отмена"]:
        await update.message.reply_text("Редактирование отменено.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU
    try:
        event_id = int(event_id_str)
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите корректный числовой ID мероприятия:")
        return MOD_EVENT_EDIT_SELECT

    event = event_db.get_event_by_id(event_id)
    if not event:
        await update.message.reply_text("Мероприятие не найдено. Введите корректный ID или 'Отмена':")
        return MOD_EVENT_EDIT_SELECT

    context.user_data["edit_event_id"] = event_id
    # Выводим клавиатуру выбора поля для редактирования
    keyboard = ReplyKeyboardMarkup([
        ["Название", "Дата"],
        ["Время", "Регион"],
        ["Описание", "Теги"],
        ["Код", "Отмена"]
    ], resize_keyboard=True)
    await update.message.reply_text("Выберите поле для редактирования:", reply_markup=keyboard)
    return MOD_EVENT_EDIT_FIELD

async def handle_event_edit_field(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    field = update.message.text.strip()
    if field in ["Отмена", "❌ Отмена"]:
        await update.message.reply_text("Редактирование отменено.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU
    valid_fields = ["Название", "Дата", "Время", "Регион", "Описание", "Теги", "Код"]
    if field not in valid_fields:
        await update.message.reply_text("Пожалуйста, выберите одно из предложенных полей.")
        return MOD_EVENT_EDIT_FIELD

    context.user_data["edit_field"] = field
    await update.message.reply_text(f"Введите новое значение для поля {field}:", reply_markup=get_cancel_keyboard())
    return MOD_EVENT_EDIT_VALUE

async def handle_event_edit_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text.strip()
    if new_value in ["Отмена", "❌ Отмена"]:
        await update.message.reply_text("Редактирование отменено.", reply_markup=get_mod_menu_keyboard())
        return MOD_MENU

    event_id = context.user_data.get("edit_event_id")
    field = context.user_data.get("edit_field")
    if not event_id or not field:
        await update.message.reply_text("Ошибка: не удалось определить мероприятие или поле.")
        return MOD_MENU

    # Отображаем понятные названия полей в БД
    field_mapping = {
        "Название": "name",
        "Дата": "event_date",
        "Время": "start_time",
        "Регион": "city",
        "Описание": "description",
        "Теги": "tags",
        "Код": "code"
    }
    db_field = field_mapping.get(field)
    try:
        # Предполагается, что в модели EventModel добавлен метод update_event_field
        event_db.update_event_field(event_id, db_field, new_value)
        await update.message.reply_text(f"Поле {field} успешно обновлено.", reply_markup=get_mod_menu_keyboard())
    except Exception as e:
        logger.error(f"Ошибка при обновлении мероприятия: {e}")
        await update.message.reply_text("Произошла ошибка при обновлении мероприятия.", reply_markup=get_mod_menu_keyboard())
    return MOD_MENU

@role_required("admin")
async def export_events_by_project_csv(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрашивает у администратора ID проекта для экспорта мероприятий."""
    await update.message.reply_text(
        "Введите ID проекта для выгрузки мероприятий:",
        reply_markup=get_cancel_keyboard()
    )
    return ADMIN_PROJECT_EXPORT

async def handle_project_export_input(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    project_id_text = update.message.text.strip()
    if project_id_text in ["❌ Отмена", "Отмена"]:
        await update.message.reply_text("Экспорт отменён.", reply_markup=get_admin_menu_keyboard())
        return ADMIN_MENU
    try:
        project_id = int(project_id_text)
    except ValueError:
        await update.message.reply_text(
            "Пожалуйста, введите корректное числовое значение ID проекта.",
            reply_markup=get_cancel_keyboard()
        )
        return ADMIN_PROJECT_EXPORT

    from database.core import Database
    db = Database()
    with db.connect() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''SELECT id, name, event_date, start_time, city, creator, description,
                      participation_points, participants_count, tags, code, owner, project_id
               FROM events WHERE project_id = ?''',
            (project_id,)
        )
        events = cursor.fetchall()

    if not events:
        await update.message.reply_text(
            "Для заданного ID проекта мероприятия не найдены.",
            reply_markup=get_admin_menu_keyboard()
        )
        return ADMIN_MENU

    import os, csv
    os.makedirs("data", exist_ok=True)
    temp_file = os.path.join("data", f"events_project_{project_id}_export.csv")
    fieldnames = ["id", "name", "event_date", "start_time", "city", "creator", "description",
                  "participation_points", "participants_count", "tags", "code", "owner", "project_id"]

    with open(temp_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for event in events:
            row = dict(event)
            writer.writerow({
                "id": row.get("id", ""),
                "name": row.get("name", ""),
                "event_date": row.get("event_date", ""),
                "start_time": row.get("start_time", ""),
                "city": row.get("city", ""),
                "creator": row.get("creator", ""),
                "description": row.get("description", ""),
                "participation_points": row.get("participation_points", 0),
                "participants_count": row.get("participants_count", 0),
                "tags": row.get("tags", ""),
                "code": row.get("code", ""),
                "owner": row.get("owner", ""),
                "project_id": row.get("project_id", "")
            })

    with open(temp_file, "rb") as f:
        await update.message.reply_document(
            document=f,
            filename=os.path.basename(temp_file),
            caption=f"Выгрузка мероприятий для проекта с ID {project_id} в CSV формате"
        )

    os.remove(temp_file)
    return ADMIN_MENU