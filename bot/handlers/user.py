import logging
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from bot.states import MAIN_MENU, AI_CHAT, VOLUNTEER_HOME, GUEST_HOME, GUEST_REGISTRATION, GUEST_TAG_SELECTION, PROFILE_MENU, WAIT_FOR_PROFILE_UPDATE, PROFILE_TAG_SELECTION, PROFILE_UPDATE_SELECTION, GUEST_CITY_SELECTION, PROFILE_CITY_SELECTION
from bot.keyboards import get_city_selection_keyboard, get_tag_selection_keyboard, get_main_menu_keyboard, get_volunteer_home_keyboard, get_profile_menu_keyboard, get_events_keyboard, get_profile_update_keyboard
from database.db import Database
from services.ai_service import RecommendationAgent

db = Database()
logger = logging.getLogger(__name__)

async def handle_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    if not user:
        await update.message.reply_text("Добро пожаловать! Вы не зарегистрированы. Начинаем регистрацию.")
        return await handle_guest_registration(update, context)
    if text == "🏠 Дом Волонтера":
        await update.message.reply_text("Добро пожаловать в домашнюю страницу волонтера!", reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    elif text in ["🤖 ИИ Помощник", "🤖 ИИ Волонтера"]:
        await update.message.reply_text("Напишите ваш вопрос для ИИ:")
        return AI_CHAT
    elif text == "Мероприятия":
        context.user_data["events_page"] = 0
        await update.message.reply_text("Список мероприятий:", reply_markup=get_main_menu_keyboard())
        return await handle_events(update, context)
    elif text and "регистрация" in text.lower():
        user = update.effective_user
        first_name = user.first_name if user.first_name else "Пользователь"
        await update.message.reply_text(f"Вы выбрали регистрацию.\nВаше имя: {first_name}\nДалее выберите ваш город для завершения регистрации.")
        return await handle_guest_registration(update, context)
    elif text == "Выход":
        await update.message.reply_text("Вы вышли из меню. Для повторного входа отправьте /start")
        return MAIN_MENU
    else:
        await update.message.reply_text("Неизвестная команда. Попробуйте ещё раз.")
        return MAIN_MENU

async def handle_ai_chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.message.text
    user_id = update.effective_user.id
    agent = RecommendationAgent()
    response = agent.process_query(query, user_id)
    await update.message.reply_text(response)
    return AI_CHAT

async def handle_volunteer_home(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Профиль":
        user = db.get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text("❌ Ошибка: профиль не найден")
            return MAIN_MENU
            
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

        # Форматируем теги
        tags = [tag.strip() for tag in user.get("tags", "").split(",") if tag.strip()]
        tags_text = "• " + "\n• ".join(escape_markdown_v2(tag) for tag in tags) if tags else "Не указаны"
        
        # Формируем сообщение
        reply = (
            f"👤 *Профиль волонтера*\n\n"
            f"📝 *Имя:* {escape_markdown_v2(user.get('first_name', 'Не указано'))}\n"
            f"🌟 *Роль:* {escape_markdown_v2(user.get('role', 'Волонтер'))}\n"
            f"🏆 *Баллы:* {user.get('score', 0)}\n"
            f"🏙️ *Город:* {escape_markdown_v2(user.get('city', 'Не указан'))}\n\n"
            f"🏷️ *Интересующие направления:*\n{tags_text}\n\n"
        )
        
        if registered_events:
            reply += f"📅 *Зарегистрированные мероприятия:*\n" + "\n".join(registered_events)
        else:
            reply += "📅 *Зарегистрированные мероприятия:* Нет активных регистраций"

        await update.message.reply_markdown_v2(reply, reply_markup=get_profile_menu_keyboard())
        return PROFILE_MENU
    if text == "Выход":
        reply = f"Возвращаемся в главное меню!"
        await update.message.reply_text(reply, reply_markup=get_main_menu_keyboard())
        return MAIN_MENU
    else:
        await update.message.reply_text("Команда не распознана. Выберите действие.")
        return VOLUNTEER_HOME

async def handle_guest_registration(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    first_name = user.first_name if user.first_name else "Пользователь"
    context.user_data["pending_first_name"] = first_name
    await update.message.reply_text("Для завершения регистрации, пожалуйста, выберите ваш город:", reply_markup=get_city_selection_keyboard())
    return GUEST_CITY_SELECTION

async def handle_city_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    page = context.user_data.get("city_page", 0)
    if data.startswith("city:"):
        city = data.split(":", 1)[1]
        # Если город уже выбран, убираем его из выбранных
        if context.user_data.get("pending_city") == city:
            context.user_data.pop("pending_city", None)
            await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(page=page))
        else:
            context.user_data["pending_city"] = city
            await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(selected_cities=[city], page=page))
        return GUEST_CITY_SELECTION
    elif data.startswith("city_next:") or data.startswith("city_prev:"):
        try:
            page = int(data.split(":", 1)[1])
        except ValueError:
            page = 0
        if data.startswith("city_next:"):
            page += 1
        else:
            page -= 1
        context.user_data["city_page"] = page
        selected = [context.user_data["pending_city"]] if "pending_city" in context.user_data else []
        await query.edit_message_reply_markup(reply_markup=get_city_selection_keyboard(selected_cities=selected, page=page))
        return GUEST_CITY_SELECTION
    elif data == "done_cities":
        if not context.user_data.get("pending_city"):
            await query.answer("Пожалуйста, выберите город перед тем как продолжить")
            return GUEST_CITY_SELECTION
        await query.edit_message_text("Теперь выберите теги, которые вас интересуют:", reply_markup=get_tag_selection_keyboard())
        return GUEST_TAG_SELECTION
    return GUEST_CITY_SELECTION

async def handle_tag_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    selected_tags = context.user_data.get("pending_tags", [])
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
                logger.error(f"Ошибка при обновлении клавиатуры тегов: {e}")
        return GUEST_TAG_SELECTION
    elif data == "done":
        pending_first_name = context.user_data.get("pending_first_name", "Пользователь")
        db.save_user(user_id, pending_first_name)
        pending_city = context.user_data.get("pending_city", "")
        if pending_city:
            db.update_user_city(user_id, pending_city)
        db.update_user_tags(user_id, ",".join(selected_tags))
        try:
            await query.message.reply_text(
                "Регистрация успешно завершена! Добро пожаловать!",
                reply_markup=get_main_menu_keyboard()
            )
            await query.message.delete()
        except Exception as e:
            logger.error(f"Ошибка при обновлении сообщения после регистрации: {e}")
            
        context.user_data.pop("pending_first_name", None)
        context.user_data.pop("pending_city", None)
        context.user_data.pop("pending_tags", None)
        context.user_data.pop("city_page", None)
        return MAIN_MENU
    return GUEST_TAG_SELECTION

def escape_markdown_v2(text):
    """Экранирует специальные символы для Markdown V2."""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    return text

async def handle_profile_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    text = update.message.text
    if text == "Изменить информацию":
        await update.message.reply_text("Что вы хотите изменить?", reply_markup=get_profile_update_keyboard())
        return PROFILE_UPDATE_SELECTION
    elif text == "Выход":
        await update.message.reply_text("Возвращаемся в главное меню", reply_markup=get_volunteer_home_keyboard())
        return VOLUNTEER_HOME
    else:
        await update.message.reply_text("Неизвестная команда. Попробуйте ещё раз.")
        return PROFILE_MENU

async def handle_contact_update(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_first_name = update.message.text.strip()
    user_id = update.effective_user.id
    db.update_first_name(user_id, new_first_name)
    await update.message.reply_text(f"Ваше имя обновлено на: {new_first_name}", reply_markup=get_profile_menu_keyboard())
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
            await query.edit_message_text("Выберите новые теги:", reply_markup=get_tag_selection_keyboard())
            return PROFILE_TAG_SELECTION
        elif option == "city":
            await query.edit_message_text("Выберите новый город:", reply_markup=get_city_selection_keyboard())
            return PROFILE_CITY_SELECTION
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
                logger.error(f"Ошибка при обновлении клавиатуры профиля: {e}")
        return PROFILE_TAG_SELECTION
    elif data == "done_tags":
        db.update_user_tags(user_id, ",".join(selected_tags))
        try:
            await query.edit_message_text("Ваши теги обновлены!")
        except Exception as e:
            if "not modified" in str(e):
                pass
            else:
                logger.error(f"Ошибка при редактировании сообщения профиля: {e}")
        return PROFILE_MENU
    return PROFILE_TAG_SELECTION

async def handle_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query if update.callback_query else None
    if query:
        await query.answer()
    user_id = update.effective_user.id
    user = db.get_user(user_id)
    page = context.user_data.get("events_page", 0)
    if user and user.get("city"):
        city = user["city"]
        events = db.get_events_by_city(city, limit=5, offset=page * 5)
        total_events = db.get_events_count_by_city(city)
        if not events:
            events = db.get_events(limit=5, offset=page * 5)
            total_events = db.get_events_count()
    else:
        events = db.get_events(limit=5, offset=page * 5)
        total_events = db.get_events_count()
    registered = [e.strip() for e in user.get("registered_events", "").split(",") if e.strip()] if user else []
    if query:
        await query.edit_message_text("Список мероприятий:", reply_markup=get_events_keyboard(events, page, 5, total_events, registered_events=registered))
    else:
        await update.message.reply_text("Список мероприятий:", reply_markup=get_events_keyboard(events, page, 5, total_events, registered_events=registered))
    return GUEST_HOME

async def handle_events_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("register_event:"):
        event_id = data.split(":", 1)[1]
        user_id = update.effective_user.id
        
        # Проверяем, не зарегистрирован ли уже пользователь
        if db.is_user_registered_for_event(user_id, event_id):
            await query.answer("Вы уже зарегистрированы на это мероприятие")
            return GUEST_HOME
            
        # Получаем информацию о мероприятии
        event = db.get_event_by_id(int(event_id))
        if not event:
            await query.answer("Мероприятие не найдено")
            return GUEST_HOME
            
        user = db.get_user(user_id)
        reg_events = user.get("registered_events", "")
        events_list = [e.strip() for e in reg_events.split(",") if e.strip()]
        events_list.append(event_id)
        db.update_user_registered_events(user_id, ",".join(events_list))
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
        await query.edit_message_text("Возвращаемся в главное меню", reply_markup=get_main_menu_keyboard())
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
            try:
                await query.message.reply_text(
                    f"Ваш город успешно обновлен на: {city}",
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
