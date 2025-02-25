import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.states import MAIN_MENU, AI_CHAT, VOLUNTEER_HOME, GUEST_HOME, PROFILE_MENU, WAIT_FOR_PROFILE_UPDATE, PROFILE_TAG_SELECTION, PROFILE_UPDATE_SELECTION, REGISTRATION_TAG_SELECTION, REGISTRATION_CITY_SELECTION, PROFILE_CITY_SELECTION, EVENT_DETAILS
from bot.keyboards import get_city_selection_keyboard, get_tag_selection_keyboard, get_main_menu_keyboard, get_volunteer_home_keyboard, get_profile_menu_keyboard, get_events_keyboard, get_profile_update_keyboard, get_event_details_keyboard, get_events_filter_keyboard
from database.db import Database
from services.ai_service import RecommendationAgent
from config import ADMIN_ID

db = Database()
logger = logging.getLogger(__name__)

def escape_markdown_v2(text):
    """Экранирует специальные символы для Markdown V2."""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

def format_event_details(event):
    """Форматирует детальную информацию о мероприятии."""
    # Получаем название мероприятия из тегов
    name = ""
    description = ""
    if event.get("tags"):
        parts = event["tags"].split(";")
        for part in parts:
            if "Название:" in part:
                name = part.split("Название:")[1].strip()
            elif "Описание:" in part:
                description = part.split("Описание:")[1].strip()
    
    if not name:
        name = f"Мероприятие #{event['id']}"
    
    # Форматируем сообщение
    message = (
        f"*🎯 {escape_markdown_v2(name)}*\n\n"
        f"📅 *Дата:* {escape_markdown_v2(event['event_date'])}\n"
        f"🕒 *Время:* {escape_markdown_v2(event['start_time'])}\n"
        f"📍 *Город:* {escape_markdown_v2(event['city'])}\n"
        f"👤 *Организатор:* {escape_markdown_v2(event['creator'])}\n"
        f"👥 *Количество участников:* {escape_markdown_v2(str(event['participants_count']))}\n"
        f"🏆 *Баллы за участие:* {escape_markdown_v2(str(event['participation_points']))}\n"
    )
    
    if description:
        message += f"\n📝 *Описание:*\n{escape_markdown_v2(description)}\n"
    
    return message

def create_shareable_event_message(event):
    """Создает текстовое сообщение о мероприятии для отправки другим пользователям."""
    # Получаем название мероприятия из тегов
    name = ""
    description = ""
    if event.get("tags"):
        parts = event["tags"].split(";")
        for part in parts:
            if "Название:" in part:
                name = part.split("Название:")[1].strip()
            elif "Описание:" in part:
                description = part.split("Описание:")[1].strip()
    
    if not name:
        name = f"Мероприятие #{event['id']}"
    
    # Форматируем сообщение в обычном тексте (без Markdown)
    message = (
        f"🎯 {name}\n\n"
        f"📅 Дата: {event['event_date']}\n"
        f"🕒 Время: {event['start_time']}\n"
        f"📍 Город: {event['city']}\n"
        f"👤 Организатор: {event['creator']}\n"
        f"👥 Количество участников: {event['participants_count']}\n"
        f"🏆 Баллы за участие: {event['participation_points']}\n"
    )
    
    if description:
        message += f"\n📝 Описание:\n{description}\n"
    
    return message

def format_profile_message(user):
    """Форматирует сообщение профиля пользователя с информацией о бонусах."""
    # Получаем список мероприятий пользователя
    registered_events = []
    if user.get("registered_events"):
        event_ids = [e.strip() for e in user["registered_events"].split(",") if e.strip()]
        for event_id in event_ids:
            try:
                event = db.get_event_by_id(int(event_id))
                if event:
                    name = ""
                    if event.get("tags"):
                        parts = event["tags"].split(";")
                        for part in parts:
                            if "Название:" in part:
                                name = part.split("Название:")[1].strip()
                                break
                    if not name:
                        name = f"Мероприятие #{event['id']}"
                    registered_events.append(f"• {escape_markdown_v2(name)} \\({escape_markdown_v2(event['event_date'])} {escape_markdown_v2(event['start_time'])}\\)")
            except:
                continue

    # Форматируем интересы
    interests = [tag.strip() for tag in user.get("tags", "").split(",") if tag.strip()]
    interests_text = "• " + "\n• ".join(escape_markdown_v2(interest) for interest in interests) if interests else "Не указаны"
    
    # Получаем количество баллов и добавляем информацию о доступных наградах
    score = user.get("score", 0)
    
    # Формируем сообщение
    reply = (
        f"👤 *Профиль волонтера*\n\n"
        f"📝 *Имя:* {escape_markdown_v2(user.get('first_name', 'Не указано'))}\n"
        f"🌟 *Роль:* {escape_markdown_v2(user.get('role', 'Волонтер'))}\n"
        f"🏆 *Баллы:* {escape_markdown_v2(str(score))}\n"
        f"🏙️ *Город:* {escape_markdown_v2(user.get('city', 'Не указан'))}\n\n"
        f"🏷️ *Интересы:*\n{interests_text}\n\n"
    )
    
    if registered_events:
        reply += f"📅 *Зарегистрированные мероприятия:*\n" + "\n".join(registered_events)
    else:
        reply += "📅 *Зарегистрированные мероприятия:* Нет активных регистраций"
        
    return reply

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    
    if not user:
        await update.message.reply_text("Добро пожаловать! Вы не зарегистрированы. Начинаем регистрацию.")
        return await handle_registration(update, context)
    
    # Проверяем роль пользователя
    user_role = user.get("role", "user")
    
    # Обработка общих кнопок для всех ролей
    if text == "🏠 Дом Волонтера":
        await update.message.reply_text("Добро пожаловать в домашнюю страницу волонтера!", reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    elif text in ["🤖 ИИ Помощник", "🤖 ИИ Волонтера"]:
        await update.message.reply_text("Напишите ваш вопрос для ИИ:")
        return AI_CHAT
    elif text == "Мероприятия":
        context.user_data["events_page"] = 0
        await update.message.reply_text("Список мероприятий:", reply_markup=get_main_menu_keyboard(role=user_role))
        return await handle_events(update, context)
    elif text and "регистрация" in text.lower():
        user = update.effective_user
        first_name = user.first_name if user.first_name else "Пользователь"
        await update.message.reply_text(f"Вы выбрали регистрацию.\nВаше имя: {first_name}\nДалее выберите ваш город для завершения регистрации.")
        return await handle_registration(update, context)
    elif text == "Выход":
        await update.message.reply_text("Вы вышли из меню. Для повторного входа отправьте /start")
        return MAIN_MENU
    # Если текст не соответствует ни одной из кнопок
    else:
        # Проверяем, не является ли это командой администратора
        if user_role == "admin" and text.startswith("/"):
            # Пропускаем обработку команд администратора, они будут обработаны другими обработчиками
            return MAIN_MENU
        
        await update.message.reply_text("Неизвестная команда. Попробуйте ещё раз.")
        return MAIN_MENU

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    # Проверяем, не хочет ли пользователь выйти
    if query.lower() in ["выход", "назад", "вернуться", "меню", "главное меню"]:
        await update.message.reply_text("Возвращаемся в главное меню", reply_markup=get_main_menu_keyboard(role=user_role))
        return MAIN_MENU
        
    agent = RecommendationAgent()
    response = agent.process_query(query, user_id)
    await update.message.reply_text(response)
    return AI_CHAT

async def handle_volunteer_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    if text == "Профиль":
        user = db.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ Ошибка: профиль не найден")
            return MAIN_MENU
            
        # Используем функцию format_profile_message для форматирования профиля
        reply = format_profile_message(user)
        await update.message.reply_markdown_v2(reply, reply_markup=get_profile_menu_keyboard())
        return PROFILE_MENU
    elif text == "Текущие мероприятия":
        # Инициализируем страницу мероприятий
        context.user_data["events_page"] = 0
        # Сбрасываем фильтр тегов, если он был установлен
        if "selected_tag" in context.user_data:
            context.user_data.pop("selected_tag", None)
        # Вызываем функцию обработки мероприятий
        return await handle_events(update, context)
    elif text == "Информация":
        # Отображаем информацию о боте
        info_text = (
            f"*ℹ️ Информация о боте*\n\n"
            f"Этот бот помогает волонтерам находить и регистрироваться на мероприятия\\.\n\n"
            f"*Основные функции:*\n"
            f"• Просмотр списка мероприятий\n"
            f"• Фильтрация мероприятий по тегам\n"
            f"• Регистрация на мероприятия\n"
            f"• Управление профилем\n"
            f"• Накопление бонусных баллов\n\n"
            f"Для возврата в главное меню нажмите кнопку \"Выход\"\\."
        )
        await update.message.reply_markdown_v2(info_text, reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    elif text == "Бонусы":
        user = db.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ Ошибка: профиль не найден")
            return MAIN_MENU
            
        # Получаем количество баллов пользователя
        score = user.get("score", 0)
        
        # Формируем сообщение о бонусах
        reply = (
            f"🏆 *Ваши бонусы*\n\n"
            f"Текущее количество баллов: *{escape_markdown_v2(str(score))}*\n\n"
            f"За каждое посещенное мероприятие вы получаете баллы\\.\n\n"
        )
        
        await update.message.reply_markdown_v2(reply, reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    elif text == "Выход":
        reply = f"Возвращаемся в главное меню!"
        await update.message.reply_text(reply, reply_markup=get_main_menu_keyboard(role=user_role))
        return MAIN_MENU
    else:
        await update.message.reply_text("Команда не распознана. Выберите действие.")
        return VOLUNTEER_HOME

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    first_name = user.first_name if user.first_name else "Пользователь"
    user_id = user.id
    
    # Проверяем, является ли пользователь администратором
    is_admin = user_id in ADMIN_ID
    
    # Сразу создаем пользователя в базе данных и начинаем регистрацию
    try:
        role = "admin" if is_admin else "user"
        db.save_user(user_id, first_name, role=role)
        logger.info(f"Создан новый пользователь: id={user_id}, first_name={first_name}, role={role}")
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя: {e}")
        await update.message.reply_text("Произошла ошибка при регистрации. Пожалуйста, попробуйте позже.")
        return MAIN_MENU
    
    context.user_data["pending_first_name"] = first_name
    await update.message.reply_text("Для завершения регистрации, пожалуйста, выберите ваш город:", reply_markup=get_city_selection_keyboard())
    return REGISTRATION_CITY_SELECTION

async def handle_registration_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    selected_city = context.user_data.get("pending_city", "")
    page = context.user_data.get("city_page", 0)
    if data.startswith("city:"):
        city = data.split(":", 1)[1]
        # Если город уже выбран, убираем его из выбранных
        if selected_city == city:
            context.user_data.pop("pending_city", None)
            await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(page=page))
        # Если город не выбран, добавляем его в выбранные
        else:
            context.user_data["pending_city"] = city
            await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(selected_cities=[city], page=page))
        return REGISTRATION_CITY_SELECTION
    # Перелистывание страниц
    elif data.startswith("city_next:") or data.startswith("city_prev:"):
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        # Следующая страница
        if data.startswith("city_next:"):
            page += 1
        # Предыдущая страница
        else:
            page -= 1
        context.user_data["city_page"] = page
        selected = [selected_city] if selected_city else []
        await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(selected_cities=selected, page=page))
        return REGISTRATION_CITY_SELECTION
    elif data == "done_cities":
        if selected_city:
            # Сохраняем город в базу данных
            db.update_user_city(user_id, selected_city)
            logger.info(f"Сохранен город для пользователя {user_id}: {selected_city}")
        else:
            await query.edit_message_text("Пожалуйста, выберите город перед тем как продолжить", reply_markup=get_city_selection_keyboard())
            return REGISTRATION_CITY_SELECTION
        await query.edit_message_text("Теперь выберите теги, которые вас интересуют:", reply_markup=get_tag_selection_keyboard())
        return REGISTRATION_TAG_SELECTION
    return REGISTRATION_CITY_SELECTION

async def handle_registration_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    selected_tags = context.user_data.get("pending_tags", [])
    
    # Получаем информацию о пользователе
    user = db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    if data.startswith("tag:"):
        tag = data.split(":", 1)[1]
        if tag in selected_tags:
            selected_tags.remove(tag)
        else:
            selected_tags.append(tag)
        context.user_data["pending_tags"] = selected_tags
        new_markup = get_tag_selection_keyboard(selected_tags=selected_tags)
        try:
            await query.edit_message_reply_markup(reply_markup=new_markup)
        except Exception as e:
            if "not modified" in str(e):
                pass
            else:
                logger.error(f"Ошибка при обновлении списка интересов: {e}")
        return REGISTRATION_TAG_SELECTION
    elif data == "done_tags":
        # Сохраняем теги в базу данных
        if selected_tags:
            db.update_user_tags(user_id, ",".join(selected_tags))
            logger.info(f"Сохранены теги для пользователя {user_id}: {selected_tags}")
        else:
            await query.edit_message_text("Пожалуйста, выберите теги перед тем как продолжить", reply_markup=get_tag_selection_keyboard())
            return REGISTRATION_TAG_SELECTION
        try:
            await query.message.reply_text(
                "Регистрация успешно завершена! Добро пожаловать!",
                reply_markup=get_main_menu_keyboard(role=user_role)
            )
            # Вывод введенных данных
            await query.message.reply_text(
                f"👤 Имя: {context.user_data['pending_first_name']}\n"
                f"🏙 Город: {context.user_data['pending_city']}\n"
                f"🏷 Теги: {', '.join(context.user_data['pending_tags'])}"
            )
            await query.message.delete()
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения после регистрации: {e}")
            
        context.user_data.pop("pending_first_name", None)
        context.user_data.pop("pending_city", None)
        context.user_data.pop("pending_tags", None)
        return MAIN_MENU
    return REGISTRATION_TAG_SELECTION

async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    if text == "Изменить информацию":
        await update.message.reply_text("Что вы хотите изменить?", reply_markup=get_profile_update_keyboard())
        return PROFILE_UPDATE_SELECTION
    elif text == "Выход":
        await update.message.reply_text("Возвращаемся в главное меню", reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    else:
        await update.message.reply_text("Неизвестная команда. Попробуйте ещё раз.")
        return PROFILE_MENU

async def get_profile_info(user_id: int) -> str:
    """Получает отформатированную информацию о профиле пользователя."""
    user = db.get_user(user_id)
    if not user:
        return "❌ Ошибка: профиль не найден"
        
    # Используем функцию format_profile_message для форматирования профиля
    return format_profile_message(user)

async def handle_contact_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_first_name = update.message.text.strip()
    user_id = update.effective_user.id
    db.update_first_name(user_id, new_first_name)
    profile_info = await get_profile_info(user_id)
    await update.message.reply_markdown_v2(
        f"✅ Ваше имя успешно обновлено\\!\n\n{profile_info}",
        reply_markup=get_profile_menu_keyboard()
    )
    return PROFILE_MENU

async def handle_profile_update_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("update:"):
        option = data.split(":", 1)[1]
        if option == "name":
            await query.edit_message_text("Введите ваше новое имя:")
            return WAIT_FOR_PROFILE_UPDATE
        elif option == "tags":
            # Загружаем текущие интересы пользователя
            user = db.get_user(query.from_user.id)
            current_tags = [tag.strip() for tag in user.get("tags", "").split(",") if tag.strip()]
            context.user_data["profile_tags"] = current_tags
            await query.edit_message_text("Выберите ваши интересы:", reply_markup=get_tag_selection_keyboard(selected_tags=current_tags))
            return PROFILE_TAG_SELECTION
        elif option == "city":
            await query.edit_message_text("Выберите новый город:", reply_markup=get_city_selection_keyboard())
            return PROFILE_CITY_SELECTION
        elif option == "cancel":
            # Возвращаемся в меню профиля
            user = db.get_user(query.from_user.id)
            profile_info = await get_profile_info(user.get("id"))
            await query.edit_message_text(
                f"*Ваш профиль*\n\n{profile_info}",
                parse_mode="MarkdownV2",
                reply_markup=None
            )
            return PROFILE_MENU
    await query.edit_message_text("Неизвестная команда.")
    return PROFILE_MENU

async def handle_profile_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    selected_tags = context.user_data.get("profile_tags", [])
    
    if data.startswith("tag:"):
        tag = data.split(":", 1)[1]
        if tag in selected_tags:
            selected_tags.remove(tag)
        else:
            selected_tags.append(tag)
        context.user_data["profile_tags"] = selected_tags
        try:
            await query.edit_message_reply_markup(reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags))
        except Exception as e:
            if "not modified" in str(e):
                pass
            else:
                logger.error(f"Ошибка при обновлении списка интересов: {e}")
        return PROFILE_TAG_SELECTION
    elif data == "done_tags":
        db.update_user_tags(user_id, ",".join(selected_tags))
        profile_info = await get_profile_info(user_id)
        try:
            await query.message.reply_markdown_v2(
                f"✅ Ваши интересы успешно обновлены\\!\n\n{profile_info}",
                reply_markup=get_profile_menu_keyboard()
            )
            await query.message.delete()
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения после выбора интересов: {e}")
        return PROFILE_MENU
    return PROFILE_TAG_SELECTION

async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    page = context.user_data.get("events_page", 0)
    selected_tag = context.user_data.get("selected_tag", None)
    
    # Получаем события в зависимости от выбранного фильтра
    if selected_tag and selected_tag != "all":
        if user and user.get("city"):
            city = user["city"]
            events = db.get_events_by_tag(selected_tag, limit=2, offset=page * 2)
            total_events = db.get_events_count_by_tag(selected_tag)
            if not events:
                events = db.get_events(limit=2, offset=page * 2)
                total_events = db.get_events_count()
        else:
            events = db.get_events_by_tag(selected_tag, limit=2, offset=page * 2)
            total_events = db.get_events_count_by_tag(selected_tag)
    else:
        if user and user.get("city"):
            city = user["city"]
            events = db.get_events_by_city(city, limit=2, offset=page * 2)
            total_events = db.get_events_count_by_city(city)
            if not events:
                events = db.get_events(limit=2, offset=page * 2)
                total_events = db.get_events_count()
        else:
            events = db.get_events(limit=2, offset=page * 2)
            total_events = db.get_events_count()
    
    # Проверяем, есть ли у пользователя зарегистрированные мероприятия
    registered = []
    if user and "registered_events" in user:
        registered = [e.strip() for e in user.get("registered_events", "").split(",") if e.strip()]
    
    # Формируем заголовок сообщения в зависимости от выбранного фильтра
    if selected_tag and selected_tag != "all":
        message_text = f"Список мероприятий по тегу '{selected_tag}':"
    else:
        message_text = "Список мероприятий:"
    
    # Проверяем, есть ли мероприятия для отображения
    if not events:
        message_text = "К сожалению, мероприятий не найдено."
        if query:
            await query.edit_message_text(message_text)
        else:
            await update.message.reply_text(message_text)
        return GUEST_HOME
    
    # Отображаем список мероприятий
    if query:
        await query.edit_message_text(message_text, reply_markup=get_events_keyboard(events, page, 2, total_events, registered_events=registered))
    else:
        await update.message.reply_text(message_text, reply_markup=get_events_keyboard(events, page, 2, total_events, registered_events=registered))
    return GUEST_HOME

async def handle_events_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    if data.startswith("view_event:"):
        event_id = data.split(":", 1)[1]
        event = db.get_event_by_id(int(event_id))
        if not event:
            await query.answer("Мероприятие не найдено")
            return GUEST_HOME
        
        # Отмечаем, что мы находимся в режиме просмотра деталей мероприятия
        context.user_data["viewing_event_details"] = True
        context.user_data["current_event_id"] = event_id
        
        # Форматируем информацию о мероприятии
        event_details = format_event_details(event)
        
        # Проверяем, зарегистрирован ли пользователь на это мероприятие
        is_registered = db.is_user_registered_for_event(user_id, event_id)
        
        # Отправляем сообщение с информацией о мероприятии
        await query.edit_message_text(
            event_details,
            reply_markup=get_event_details_keyboard(event_id, is_registered),
            parse_mode="MarkdownV2"
        )
        return EVENT_DETAILS
    elif data.startswith("share_event:"):
        event_id = data.split(":", 1)[1]
        event = db.get_event_by_id(int(event_id))
        if not event:
            await query.answer("Мероприятие не найдено")
            return GUEST_HOME
        
        # Создаем сообщение для отправки
        shareable_message = create_shareable_event_message(event)
        
        # Отправляем пользователю сообщение, которым он может поделиться
        await query.message.reply_text(
            "📤 Вот сообщение, которым вы можете поделиться с друзьями:"
        )
        await query.message.reply_text(
            shareable_message
        )
        
        # Возвращаемся к просмотру деталей мероприятия
        return EVENT_DETAILS
    elif data == "show_filters":
        # Показываем клавиатуру с фильтрами
        selected_tag = context.user_data.get("selected_tag", None)
        await query.edit_message_text(
            "Выберите тег для фильтрации мероприятий:",
            reply_markup=get_events_filter_keyboard(selected_tag)
        )
        return GUEST_HOME
    elif data.startswith("filter_tag:"):
        tag = data.split(":", 1)[1]
        if tag == "all":
            # Сбрасываем фильтр
            context.user_data.pop("selected_tag", None)
        else:
            # Устанавливаем фильтр по тегу
            context.user_data["selected_tag"] = tag
        
        # Сбрасываем страницу
        context.user_data["events_page"] = 0
        
        # Возвращаемся к списку мероприятий с примененным фильтром
        return await handle_events(update, context)
    elif data.startswith("register_event:"):
        event_id = data.split(":", 1)[1]
        
        # Проверяем, не зарегистрирован ли уже пользователь
        if db.is_user_registered_for_event(user_id, event_id):
            await query.answer("Вы уже зарегистрированы на это мероприятие")
            return GUEST_HOME
            
        # Получаем информацию о мероприятии
        event = db.get_event_by_id(int(event_id))
        if not event:
            await query.answer("Мероприятие не найдено")
            return GUEST_HOME
            
        # Обновляем список мероприятий пользователя
        reg_events = user.get("registered_events", "")
        events_list = [e.strip() for e in reg_events.split(",") if e.strip()]
        events_list.append(event_id)
        db.update_user_registered_events(user_id, ",".join(events_list))
        
        # Увеличиваем счетчик участников мероприятия
        db.increment_event_participants_count(int(event_id))
        
        # Получаем обновленную информацию о мероприятии
        event = db.get_event_by_id(int(event_id))
        
        # Если мы находимся в детальном просмотре, обновляем информацию
        if context.user_data.get("viewing_event_details"):
            event_details = format_event_details(event)
            await query.edit_message_text(
                event_details,
                reply_markup=get_event_details_keyboard(event_id, True),
                parse_mode="MarkdownV2"
            )
            return EVENT_DETAILS
        else:
            return await handle_events(update, context)
    elif data.startswith("unregister_event:"):
        event_id = data.split(":", 1)[1]
        
        # Проверяем, зарегистрирован ли пользователь
        if not db.is_user_registered_for_event(user_id, event_id):
            await query.answer("Вы не зарегистрированы на это мероприятие")
            return GUEST_HOME
            
        # Получаем информацию о мероприятии
        event = db.get_event_by_id(int(event_id))
        if not event:
            await query.answer("Мероприятие не найдено")
            return GUEST_HOME
            
        # Удаляем мероприятие из списка зарегистрированных
        reg_events = user.get("registered_events", "")
        events_list = [e.strip() for e in reg_events.split(",") if e.strip() and e != str(event_id)]
        db.update_user_registered_events(user_id, ",".join(events_list))
        
        # Уменьшаем счетчик участников мероприятия
        db.decrement_event_participants_count(int(event_id))
        
        # Получаем обновленную информацию о мероприятии
        event = db.get_event_by_id(int(event_id))
        
        # Если мы находимся в детальном просмотре, обновляем информацию
        if context.user_data.get("viewing_event_details"):
            event_details = format_event_details(event)
            await query.edit_message_text(
                event_details,
                reply_markup=get_event_details_keyboard(event_id, False),
                parse_mode="MarkdownV2"
            )
            return EVENT_DETAILS
        else:
            return await handle_events(update, context)
    elif data == "back_to_events":
        # Очищаем данные о просмотре деталей мероприятия
        context.user_data.pop("viewing_event_details", None)
        context.user_data.pop("current_event_id", None)
        return await handle_events(update, context)
    elif data.startswith("events_next:") or data.startswith("events_prev:"):
        page = context.user_data.get("events_page", 0)
        if data.startswith("events_next:"):
            page += 1
        else:
            page = max(0, page - 1)
        context.user_data["events_page"] = page
        return await handle_events(update, context)
    elif data == "back_to_menu":
        # Отправляем новое сообщение с клавиатурой главного меню вместо редактирования текущего
        await query.message.reply_text("Возвращаемся в главное меню", reply_markup=get_main_menu_keyboard(role=user_role))
        # Удаляем или скрываем предыдущее сообщение с инлайн-клавиатурой
        try:
            await query.message.delete()
        except Exception:
            # Если не удалось удалить, просто скрываем клавиатуру
            await query.edit_message_reply_markup(reply_markup=None)
        return MAIN_MENU
    return MAIN_MENU

async def handle_profile_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    page = context.user_data.get("profile_city_page", 0)
    if data.startswith("city:"):
        city = data.split(":", 1)[1]
        # Если город уже выбран, убираем его из выбранных
        if context.user_data.get("pending_profile_city") == city:
            context.user_data.pop("pending_profile_city", None)
            await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(page=page))
        else:
            context.user_data["pending_profile_city"] = city
            user_id = query.from_user.id
            db.update_user_city(user_id, city)
            profile_info = await get_profile_info(user_id)
            try:
                await query.message.reply_markdown_v2(
                    f"✅ Ваш город успешно обновлен\\!\n\n{profile_info}",
                    reply_markup=get_profile_menu_keyboard()
                )
                await query.message.delete()
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения после выбора города: {e}")
            return PROFILE_MENU
    elif data.startswith("city_next:") or data.startswith("city_prev:"):
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        if data.startswith("city_next:"):
            page += 1
        else:
            page -= 1
        context.user_data["profile_city_page"] = page
        selected = [context.user_data["pending_profile_city"]] if "pending_profile_city" in context.user_data else []
        await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(selected_cities=selected, page=page))
        return PROFILE_CITY_SELECTION
    elif data == "done_cities":
        if not context.user_data.get("pending_profile_city"):
            await query.answer("Пожалуйста, выберите город перед тем как продолжить")
            return PROFILE_CITY_SELECTION
        await query.edit_message_text("Выберите город из списка.")
        return PROFILE_CITY_SELECTION
    return PROFILE_CITY_SELECTION
