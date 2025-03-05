import logging
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from bot.states import (MAIN_MENU, AI_CHAT, VOLUNTEER_DASHBOARD, GUEST_DASHBOARD, PROFILE_MENU, 
                    PROFILE_UPDATE_NAME, PROFILE_TAG_SELECT, REGISTRATION_TAG_SELECT,
                    REGISTRATION_CITY_SELECT, PROFILE_CITY_SELECT, EVENT_DETAILS, MOD_MENU,
                    EVENT_CODE_REDEEM, PROFILE_EMPLOYEE_NUMBER)

from bot.keyboards import (get_ai_chat_keyboard, get_city_selection_keyboard, get_tag_selection_keyboard, get_main_menu_keyboard,
                    get_volunteer_dashboard_keyboard, get_profile_menu_keyboard, get_events_keyboard,
                    get_events_filter_keyboard, get_event_details_keyboard, get_mod_menu_keyboard)

from database import UserModel, EventModel
from services.ai_service import ContextRouterAgent
from config import ADMIN_ID
from bot.constants import CITIES, TAGS

logger = logging.getLogger(__name__)

user_db = UserModel()
event_db = EventModel()

def escape_markdown_v2(text):
    """Экранирует специальные символы для Markdown V2."""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return ''.join(f'\\{char}' if char in escape_chars else char for char in str(text))

def format_event_details(event):
    """Форматирует детали мероприятия для отображения."""
    if not event:
        return "Информация о мероприятии недоступна"

    try:
        # Форматируем сообщение с проверкой на существование полей
        message = f"*{escape_markdown_v2(event.get('name', 'Без названия'))}*\n\n"
        message += f"📅 Дата: {escape_markdown_v2(event.get('event_date', 'Не указана'))}\n"
        message += f"⏰ Время: {escape_markdown_v2(event.get('start_time', 'Не указано'))}\n"
        message += f"📍 Город: {escape_markdown_v2(event.get('city', 'Не указан'))}\n"
        message += f"👥 Организатор: {escape_markdown_v2(event.get('creator', 'Не указан'))}\n"
        message += f"\n📝 Описание: {escape_markdown_v2(event.get('description', 'Не указано'))}\n"
        message += f"\n💰 Баллы за участие: {event.get('participation_points', 0)}\n"
        message += f"👥 Количество участников: {event.get('participants_count', 0)}\n"

        return message
    except Exception as e:
        logger.error(f"Ошибка при форматировании деталей мероприятия: {e}")
        return "Ошибка при отображении информации о мероприятии"

def format_profile_message(user):
    """Форматирует сообщение профиля пользователя с информацией о бонусах."""
    # Получаем список мероприятий пользователя
    registered_events = []
    if user.get("registered_events"):
        event_ids = [e.strip() for e in user["registered_events"].split(",") if e.strip()]
        for event_id in event_ids:
            try:
                event = event_db.get_event_by_id(int(event_id))
                if event:
                    registered_events.append(
                        f"• {escape_markdown_v2(event['name'])} \\({escape_markdown_v2(event['event_date'])} {escape_markdown_v2(event['start_time'])}\\)"
                    )
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
    user = user_db.get_user(user_id)
    user_role = user.get('role', 'user') if user else 'user'

    # Добавляем логирование для отладки
    logger.info(f"Received text in main menu: '{text}', user_role: {user_role}")

    if text == "🏠 Дом Волонтера":
        await update.message.reply_text(
            "Добро пожаловать в домашнюю страницу волонтера!",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD
    
    elif text in ["🤖 ИИ Помощник", "🤖 ИИ Волонтера"]:
        await update.message.reply_text(
            "Напишите ваш вопрос для ИИ:",
            reply_markup=get_ai_chat_keyboard()
        )
        return AI_CHAT
    
    elif text == "Модерация" and user_role in ["admin", "moderator"]:
        from bot.handlers.admin import moderation_menu
        return await moderation_menu(update, context)
    
    elif text == "Администрация" and user_role == "admin":
        from bot.handlers.admin import admin_menu
        return await admin_menu(update, context)
    
    elif text.lower() == "выход":
        await update.message.reply_text(
            "Вы уже в главном меню.",
            reply_markup=get_main_menu_keyboard(role=user_role)
        )
        return MAIN_MENU
    
    else:
        await update.message.reply_text(
            "Неизвестная команда. Попробуйте ещё раз.",
            reply_markup=get_main_menu_keyboard(role=user_role)
        )
        return MAIN_MENU

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text.strip()
    if query.lower() in ["выход", "назад", "меню", "❌ отмена"]:
        context.user_data.pop("conversation_history", None)
        await update.message.reply_text("Диалог прерван. Возвращаемся в главное меню.", reply_markup=get_main_menu_keyboard())
        return MAIN_MENU

    if "conversation_history" not in context.user_data:
        context.user_data["conversation_history"] = []

    context.user_data["conversation_history"].append({"role": "user", "content": query})

    router_agent = ContextRouterAgent()
    response = router_agent.process_query(query, update.effective_user.id, context.user_data["conversation_history"])

    context.user_data["conversation_history"].append({"role": "assistant", "content": response})

    await update.message.reply_markdown(response)
    return AI_CHAT

async def handle_volunteer_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = user_db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    if text == "Профиль":
        user = user_db.get_user(update.effective_user.id)
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
            f"Для возврата в главное меню нажмите кнопку \\\"Выход\\\"\\."
        )
        await update.message.reply_markdown_v2(info_text, reply_markup=get_volunteer_dashboard_keyboard())
        return VOLUNTEER_DASHBOARD
    elif text == "Бонусы":
        user = user_db.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ Ошибка: профиль не найден")
            return MAIN_MENU

        score = user.get("score", 0)

        reply = (
            f"🏆 *Ваши бонусы*\n\n"
            f"Текущее количество баллов: *{escape_markdown_v2(str(score))}*\n\n"
            f"За каждое посещенное мероприятие вы получаете баллы\\.\n\n"
        )
        
        await update.message.reply_markdown_v2(reply, reply_markup=get_volunteer_dashboard_keyboard())
        return VOLUNTEER_DASHBOARD
    elif text == "Ввести код":
        keyboard = ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)
        await update.message.reply_text("Пожалуйста, введите код, который вам выдал модератор:", reply_markup=keyboard)
        return EVENT_CODE_REDEEM
    elif text == "Выход":
        reply = f"Возвращаемся в главное меню!"
        await update.message.reply_text(reply, reply_markup=get_main_menu_keyboard(role=user_role))
        return MAIN_MENU
    else:
        await update.message.reply_text("Команда не распознана. Выберите действие.")
        return VOLUNTEER_DASHBOARD

async def handle_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    first_name = user.first_name if user.first_name else "Пользователь"
    user_id = user.id
    telegram_tag = user.username if user.username else ""
    role = "user"
    # Сохраняем пользователя (только имя, telegram_tag и роль)
    try:
        user_db.save_user(id=user_id, first_name=first_name, telegram_tag=telegram_tag, role=role)
    except Exception as e:
        await update.message.reply_text("Произошла ошибка при регистрации. Попробуйте позже.")
        return MAIN_MENU
    await update.message.reply_text("Пожалуйста, введите ваш табельный номер (от 5 до 20 символов):")
    return PROFILE_EMPLOYEE_NUMBER


async def handle_registration_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора города при регистрации."""
    text = update.message.text
    user_id = update.effective_user.id
    page = context.user_data.get("city_page", 0)

    # Обработка кнопки отмены
    if text == "❌ Отмена":
        await update.message.reply_text(
            "Регистрация отменена. Для начала заново отправьте /start",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU

    # Обработка навигации по страницам
    if text == "⬅️ Назад":
        if page > 0:
            page -= 1
            context.user_data["city_page"] = page
            await update.message.reply_text(
                "Выберите город:",
                reply_markup=get_city_selection_keyboard(page=page)
            )
        return REGISTRATION_CITY_SELECT

    elif text == "Вперед ➡️":
        if (page + 1) * 3 < len(CITIES):  # 3 - это page_size
            page += 1
            context.user_data["city_page"] = page
            await update.message.reply_text(
                "Выберите город:",
                reply_markup=get_city_selection_keyboard(page=page)
            )
        return REGISTRATION_CITY_SELECT

    # Обработка выбора города
    if text.split(" ✔️")[0] in CITIES:  # Убираем маркер выбора, если он есть
        city = text.split(" ✔️")[0]
        # Сохраняем город в БД
        user_db.update_user_city(user_id, city)
        # Переходим к выбору тегов
        await update.message.reply_text(
            f"Город '{city}' сохранён. Теперь выберите теги, которые вас интересуют:",
            reply_markup=get_tag_selection_keyboard()
        )
        return REGISTRATION_TAG_SELECT

    # Если введен некорректный город
    await update.message.reply_text(
        "Пожалуйста, выберите город из списка.",
        reply_markup=get_city_selection_keyboard(page=page)
    )
    return REGISTRATION_CITY_SELECT

async def handle_registration_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик выбора тегов при регистрации."""
    text = update.message.text
    user_id = update.effective_user.id
    selected_tags = context.user_data.get("pending_tags", [])

    # Обработка кнопки отмены
    if text == "❌ Отмена":
        await update.message.reply_text(
            "Регистрация отменена. Для начала заново отправьте /start",
            reply_markup=get_main_menu_keyboard()
        )
        return MAIN_MENU

    # Обработка завершения выбора
    elif text == "✅ Готово":
        if not selected_tags:
            await update.message.reply_text(
                "Пожалуйста, выберите хотя бы один тег.",
                reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags)
            )
            return REGISTRATION_TAG_SELECT

        # Сохраняем выбранные теги в БД
        user_db.update_user_tags(user_id, ",".join(selected_tags))
        # Завершаем регистрацию
        await update.message.reply_text(
            "Регистрация успешно завершена! Добро пожаловать!",
            reply_markup=get_main_menu_keyboard(role="user")
        )
        # Очищаем временные данные
        context.user_data.pop("pending_tags", None)
        return MAIN_MENU

    # Обработка выбора тега
    tag = text.split(" ✓")[0]  # Убираем маркер выбора, если он есть
    if tag in TAGS:
        if tag in selected_tags:
            selected_tags.remove(tag)
        else:
            selected_tags.append(tag)
        context.user_data["pending_tags"] = selected_tags
        await update.message.reply_text(
            "Выберите интересующие вас теги (можно выбрать несколько):",
            reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags)
        )
        return REGISTRATION_TAG_SELECT

    # Если введен некорректный тег
    await update.message.reply_text(
        "Пожалуйста, выберите теги из списка.",
        reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags)
    )
    return REGISTRATION_TAG_SELECT

async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = user_db.get_user(user_id)
    user_role = user.get("role", "user") if user else "user"
    
    if text == "Изменить имя":
        await update.message.reply_text("Введите ваше новое имя:")
        return PROFILE_UPDATE_NAME
    elif text == "Изменить интересы":
        # Загружаем текущие интересы пользователя
        current_tags = [tag.strip() for tag in user.get("tags", "").split(",") if tag.strip()]
        context.user_data["profile_tags"] = current_tags
        await update.message.reply_text("Выберите ваши интересы:", reply_markup=get_tag_selection_keyboard(selected_tags=current_tags))
        return PROFILE_TAG_SELECT
    elif text == "Изменить регион":
        await update.message.reply_text("Выберите новый город:", reply_markup=get_city_selection_keyboard())
        return PROFILE_CITY_SELECT
    elif text == "Выход":
        await update.message.reply_text("Возвращаемся в главное меню", reply_markup=get_volunteer_dashboard_keyboard())
        return VOLUNTEER_DASHBOARD
    else:
        await update.message.reply_text("Неизвестная команда. Попробуйте ещё раз.")
        return PROFILE_MENU

async def get_profile_info(user_id: int) -> str:
    """Получает отформатированную информацию о профиле пользователя."""
    user = user_db.get_user(user_id)
    if not user:
        return "❌ Ошибка: профиль не найден"
        
    # Используем функцию format_profile_message для форматирования профиля
    return format_profile_message(user)

async def handle_contact_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    user = user_db.get_user(user_id)
    old_first_name = escape_markdown_v2(user.get("first_name", "Неизвестно"))
    new_first_name = escape_markdown_v2(update.message.text.strip())
    user_db.update_first_name(user_id, update.message.text.strip())
    profile_info = await get_profile_info(user_id)
    await update.message.reply_markdown_v2(
        f"✅ Ваше имя успешно изменено с {old_first_name} на {new_first_name}\\!",
        reply_markup=get_profile_menu_keyboard()
    )
    return PROFILE_MENU

async def handle_profile_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    selected_tags = context.user_data.get("profile_tags", [])
    
    # Получаем текущие интересы пользователя из БД
    user = user_db.get_user(user_id)
    old_tags = [tag.strip() for tag in user.get("tags", "").split(",") if tag.strip()]

    if text == "✅ Готово":
        if not selected_tags:
            await update.message.reply_text(
                "❗️ Пожалуйста, выберите хотя бы один интерес.",
                reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags)
            )
            return PROFILE_TAG_SELECT

        user_db.update_user_tags(user_id, ",".join(selected_tags))
        profile_info = await get_profile_info(user_id)
        
        # Форматируем старые и новые интересы для наглядного сравнения
        old_tags_formatted = "нет" if not old_tags else "\n".join([f"📌 {escape_markdown_v2(tag)}" for tag in old_tags])
        new_tags_formatted = "\n".join([f"🎯 {escape_markdown_v2(tag)}" for tag in selected_tags])
        
        # Определяем, какие теги были добавлены и удалены
        added_tags = [tag for tag in selected_tags if tag not in old_tags]
        removed_tags = [tag for tag in old_tags if tag not in selected_tags]
        
        changes_summary = []
        if added_tags:
            changes_summary.extend([f"\\+ {escape_markdown_v2(tag)}" for tag in added_tags])
        if removed_tags:
            changes_summary.extend([f"\\- {escape_markdown_v2(tag)}" for tag in removed_tags])
        
        message = [
            "🔄 *Изменение интересов*",
            "",
            "*Было:*",
            old_tags_formatted,
            "",
            "*Стало:*",
            new_tags_formatted,
            ""
        ]
        
        if changes_summary:
            message.extend([
                "*Изменения:*",
                *changes_summary
            ])
            
        await update.message.reply_markdown_v2(
            "\n".join(message),
            reply_markup=get_profile_menu_keyboard()
        )
        return PROFILE_MENU
    
    elif text == "❌ Отмена":
        await update.message.reply_text(
            "Изменение интересов отменено.",
            reply_markup=get_profile_menu_keyboard()
        )
        return PROFILE_MENU
    
    # Обработка выбора тега
    for tag in TAGS:
        if text.startswith(tag):
            if tag in selected_tags:
                selected_tags.remove(tag)
            else:
                selected_tags.append(tag)
            context.user_data["profile_tags"] = selected_tags
            await update.message.reply_text(
                "Выберите ваши интересы:",
                reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags)
            )
            return PROFILE_TAG_SELECT

    await update.message.reply_text(
        "Пожалуйста, используйте кнопки для выбора интересов.",
        reply_markup=get_tag_selection_keyboard(selected_tags=selected_tags)
    )
    return PROFILE_TAG_SELECT

async def handle_events(update, context) -> int:
    user_id = update.effective_user.id
    user = user_db.get_user(user_id)
    page = context.user_data.get("events_page", 0)
    selected_tag = context.user_data.get("selected_tag", None)

    # Получаем мероприятия в зависимости от выбранного фильтра
    if selected_tag and selected_tag != "all":
        if user and user.get("city"):
            events = event_db.get_events_by_tag(selected_tag, limit=4, offset=page * 4)
            total_events = event_db.get_events_count_by_tag(selected_tag)
            if not events:
                events = event_db.get_events(limit=4, offset=page * 4)
                total_events = event_db.get_events_count()
        else:
            events = event_db.get_events_by_tag(selected_tag, limit=4, offset=page * 4)
            total_events = event_db.get_events_count_by_tag(selected_tag)
    else:
        if user and user.get("city"):
            events = event_db.get_events_by_city(user["city"], limit=4, offset=page * 4)
            total_events = event_db.get_events_count_by_city(user["city"])
            if not events:
                events = event_db.get_events(limit=4, offset=page * 4)
                total_events = event_db.get_events_count()
        else:
            events = event_db.get_events(limit=4, offset=page * 4)
            total_events = event_db.get_events_count()

    # Получаем список зарегистрированных мероприятий пользователя
    registered = []
    if user and "registered_events" in user:
        registered = [e.strip() for e in user.get("registered_events", "").split(",") if e.strip()]

    # Формируем заголовок сообщения
    if selected_tag and selected_tag != "all":
        message_text = f"Список мероприятий по тегу '{selected_tag}':"
    else:
        message_text = "Список мероприятий:"

    # Если мероприятий нет, отправляем сообщение
    if not events:
        message_text = "К сожалению, мероприятий не найдено."
        await update.message.reply_text(message_text, reply_markup=get_volunteer_dashboard_keyboard())
        return VOLUNTEER_DASHBOARD

    # Отправляем список мероприятий с клавиатурой
    await update.message.reply_text(
        message_text,
        reply_markup=get_events_keyboard(events, page, 4, total_events, registered_events=registered)
    )
    
    # Сохраняем текущие мероприятия в контексте для дальнейшей обработки
    context.user_data["current_events"] = events
    return GUEST_DASHBOARD

async def handle_events_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = user_db.get_user(user_id)
    current_events = context.user_data.get("current_events", [])

    if not current_events:
        await update.message.reply_text(
            "Произошла ошибка при обработке мероприятий. Попробуйте снова.",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD

    # Обработка выбора мероприятия
    for event in current_events:
        name = event.get("name")

        event_text = f"✨ {name}"
        if str(event['id']) in user.get("registered_events", "").split(","):
            event_text += " ✅"

        if text == event_text:
            # Показываем детали мероприятия
            event_details = format_event_details(event)
            is_registered = event_db.is_user_registered_for_event(user_id, str(event['id']))
            context.user_data["current_event_id"] = str(event['id'])
            await update.message.reply_markdown_v2(
                event_details,
                reply_markup=get_event_details_keyboard(event['id'], is_registered)
            )
            return EVENT_DETAILS

    # Обработка навигации
    if text == "⬅️ Назад":
        page = context.user_data.get("events_page", 0)
        if page > 0:
            context.user_data["events_page"] = page - 1
            return await handle_events(update, context)

    elif text == "Вперед ➡️":
        page = context.user_data.get("events_page", 0)
        context.user_data["events_page"] = page + 1
        return await handle_events(update, context)

    # Обработка фильтров
    elif text == "🔍 Фильтры":
        selected_tag = context.user_data.get("selected_tag", None)
        await update.message.reply_text(
            "Выберите тег для фильтрации мероприятий:",
            reply_markup=get_events_filter_keyboard(selected_tag)
        )
        return GUEST_DASHBOARD

    elif text == "Все мероприятия":
        context.user_data.pop("selected_tag", None)
        context.user_data["events_page"] = 0
        return await handle_events(update, context)

    elif text == "❌ Отмена":
        return await handle_events(update, context)

    elif text == "❌ Выход":
        await update.message.reply_text(
            "Возвращаемся в главное меню",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD

    # Обработка выбора тега
    for tag in TAGS:
        if text.startswith(tag):
            context.user_data["selected_tag"] = tag
            context.user_data["events_page"] = 0
            return await handle_events(update, context)

    return GUEST_DASHBOARD

async def handle_profile_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    page = context.user_data.get("city_page", 0)

    if text == "❌ Отмена":
        await update.message.reply_text(
            "Изменение города отменено.",
            reply_markup=get_profile_menu_keyboard()
        )
        # Очищаем временные данные
        context.user_data.pop("city_page", None)
        return PROFILE_MENU

    elif text == "⬅️ Назад":
        if page > 0:
            page -= 1
            context.user_data["city_page"] = page
            await update.message.reply_text(
                "Выберите город:",
                reply_markup=get_city_selection_keyboard(page=page)
            )
        return PROFILE_CITY_SELECT

    elif text == "Вперед ➡️":
        if (page + 1) * 3 < len(CITIES):  # 3 - это page_size
            page += 1
            context.user_data["city_page"] = page
            await update.message.reply_text(
                "Выберите город:",
                reply_markup=get_city_selection_keyboard(page=page)
            )
        return PROFILE_CITY_SELECT

    # Обработка выбора города
    for city in CITIES:
        if text.startswith(city):
            # Получаем старый город из базы данных
            user = user_db.get_user(user_id)
            old_city = escape_markdown_v2(user.get("city", "Неизвестно"))
            escaped_city = escape_markdown_v2(city)
            
            # Сразу обновляем город в базе данных
            user_db.update_user_city(user_id, city)
            
            await update.message.reply_markdown_v2(
                f"✅ Ваш город успешно изменен с {old_city} на {escaped_city}\\!",
                reply_markup=get_profile_menu_keyboard()
            )
            
            # Очищаем временные данные
            context.user_data.pop("city_page", None)
            return PROFILE_MENU

    await update.message.reply_text(
        "Пожалуйста, используйте кнопки для выбора города.",
        reply_markup=get_city_selection_keyboard(page=page)
    )
    return PROFILE_CITY_SELECT

async def handle_moderation_menu_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Добавить мероприятия":
        await update.message.reply_text("Функционал модерирования мероприятий в разработке.")
    elif text == "Изменить мероприятие":
        await update.message.reply_text("Функционал модерирования пользователей в разработке.")
    elif text == "Вернуться в главное меню":
        from bot.keyboards import get_main_menu_keyboard
        user_record = user_db.get_user(update.effective_user.id)
        role = user_record.get("role") if user_record else "user"
        await update.message.reply_text("Возвращаемся в главное меню.", reply_markup=get_main_menu_keyboard(role=role))
        return MAIN_MENU

    from bot.keyboards import get_mod_menu_keyboard
    await update.message.reply_text("Меню модерирования:", reply_markup=get_mod_menu_keyboard())
    return MOD_MENU


async def handle_code_redemption(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    # TODO: сделать сохранение истории пройденных мероприятий
    # TODO: в том числе и для того, чтобы нельзя было пройти одно и тоже мероприятие дважды
    """Обработчик ввода кода мероприятия."""
    text = update.message.text
    user_id = update.effective_user.id

    keyboard = ReplyKeyboardMarkup([["❌ Отмена"]], resize_keyboard=True)
    
    if text == "❌ Отмена":
        await update.message.reply_text(
            "Ввод кода отменен.",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD
        
    try:
        events = event_db.get_all_events()
        found_event = None
        for event in events:
            if event.get("code") == text:
                found_event = event
                break

        if not found_event:
            await update.message.reply_text(
                "❌ Неверный код мероприятия. Попробуйте еще раз или нажмите 'Отмена'.",
                reply_markup=keyboard
            )
            return EVENT_CODE_REDEEM
            
        # Проверяем, был ли зарегистрирован пользователь на мероприятие
        if event_db.is_user_registered_for_event(user_id, str(found_event['id'])):
            # Начисляем баллы
            user = user_db.get_user(user_id)
            points = found_event.get("participation_points", 0)
            current_score = user.get("score", 0)
            user_db.update_user_score(user_id, current_score + points)
            user_db.unregister_user_from_event(user_id, str(found_event['id']))
            
            await update.message.reply_markdown(
                f"Мероприятие: *{found_event['name']}*\n"
                f"Начислено баллов: *{points}*\n"
                f"Ваш текущий баланс: *{current_score + points}* баллов",
                reply_markup=get_volunteer_dashboard_keyboard()
            )
        else:
            await update.message.reply_text(
                "❌ Вы не были зарегистрированы на это мероприятие.",
                reply_markup=get_volunteer_dashboard_keyboard()
            )
        
        return MAIN_MENU
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кода мероприятия: {e}")
        await update.message.reply_text(
            "❌ Произошла ошибка при обработке кода. Пожалуйста, попробуйте позже.",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD

async def handle_employee_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    employee_number_str = update.message.text.strip()
    if not (employee_number_str.isdigit() and 20 >= len(employee_number_str) >= 5):
        await update.message.reply_text("Пожалуйста, введите корректный табельный номер – от 5 до 20 символов.")
        return PROFILE_EMPLOYEE_NUMBER
    employee_number = int(employee_number_str)
    # Обновляем данные пользователя с табельным номером
    user_db.update_user_employee_number(user_id=user_id, employee_number=employee_number)
    await update.message.reply_text("Теперь выберите ваш город:", reply_markup=get_city_selection_keyboard())
    return REGISTRATION_CITY_SELECT

async def update_to_state(query, text: str, reply_markup=None):
    """
    Обновляет сообщение, убирая inline-клавиатуру и отправляя новое сообщение с нужным состоянием.
    Если используется query, обновляем текущее сообщение, иначе отправляем новое.
    """
    try:
        # Если возможно, изменяем текст текущего сообщения и убираем клавиатуру
        await query.edit_message_text(text, reply_markup=reply_markup)
    except Exception:
        # Если не удалось, отправляем новое сообщение
        await query.message.reply_text(text, reply_markup=reply_markup)

async def handle_event_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    event_id = context.user_data.get("current_event_id")

    if not event_id:
        await update.message.reply_text(
            "Произошла ошибка при просмотре мероприятия. Попробуйте снова.",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD

    if text == "⬅️ Назад к списку":
        context.user_data.pop("current_event_id", None)
        return await handle_events(update, context)

    elif text == "❌ Выход":
        context.user_data.pop("current_event_id", None)
        await update.message.reply_text(
            "Возвращаемся в главное меню",
            reply_markup=get_volunteer_dashboard_keyboard()
        )
        return VOLUNTEER_DASHBOARD

    elif text == "✅ Зарегистрироваться":
        # Получаем информацию о пользователе и мероприятии
        user = user_db.get_user(user_id)
        event = event_db.get_event_by_id(int(event_id))
        
        if not event:
            await update.message.reply_text("❌ Мероприятие не найдено.")
            return VOLUNTEER_DASHBOARD

        # Проверяем, не зарегистрирован ли уже пользователь
        if event_db.is_user_registered_for_event(user_id, event_id):
            await update.message.reply_text("❌ Вы уже зарегистрированы на это мероприятие.")
            return EVENT_DETAILS

        try:
            # Добавляем мероприятие в список зарегистрированных
            registered_events = user.get("registered_events", "").split(",")
            registered_events = [e.strip() for e in registered_events if e.strip()]
            registered_events.append(str(event_id))
            user_db.update_user_registered_events(user_id, ",".join(registered_events))

            # Увеличиваем счетчик участников
            if not event_db.increment_event_participants_count(int(event_id)):
                logger.error(f"Не удалось увеличить счетчик участников для мероприятия {event_id}")
            
            await update.message.reply_text(
                f"✅ Вы успешно зарегистрировались на мероприятие \"{event.get('name')}\"!"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации на мероприятие: {e}")
            await update.message.reply_text("❌ Произошла ошибка при регистрации на мероприятие.")
        
        return EVENT_DETAILS

    elif text == "❌ Отменить регистрацию":
        # Получаем информацию о пользователе и мероприятии
        user = user_db.get_user(user_id)
        event = event_db.get_event_by_id(int(event_id))
        
        if not event:
            await update.message.reply_text("❌ Мероприятие не найдено.")
            return VOLUNTEER_DASHBOARD

        try:
            # Удаляем мероприятие из списка зарегистрированных
            registered_events = user.get("registered_events", "").split(",")
            registered_events = [e.strip() for e in registered_events if e.strip() and e != str(event_id)]
            user_db.update_user_registered_events(user_id, ",".join(registered_events))
            
            # Уменьшаем счетчик участников
            if not event_db.decrement_event_participants_count(int(event_id)):
                logger.error(f"Не удалось уменьшить счетчик участников для мероприятия {event_id}")
            
            await update.message.reply_text(
                f"✅ Регистрация на мероприятие \"{event.get('name')}\" отменена."
            )
            
        except Exception as e:
            logger.error(f"Ошибка при отмене регистрации: {e}")
            await update.message.reply_text("❌ Произошла ошибка при отмене регистрации.")
        
        return EVENT_DETAILS

    return EVENT_DETAILS
