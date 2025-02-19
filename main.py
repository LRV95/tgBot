import logging
import os
import csv
import openpyxl
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler, ContextTypes
from config import TOKEN, ADMIN_ID
from source.database import Database
from source.agents import RecommendationAgent

# Состояния диалога
MAIN_MENU = 0
WAIT_FOR_CSV = 1
AI_CHAT = 2
VOLUNTEER_HOME = 3
GUEST_HOME = 4
GUEST_REGISTRATION = 5
PROFILE_MENU = 6
WAIT_FOR_PROFILE_UPDATE = 7         # для обновления контактной информации
GUEST_TAG_SELECTION = 8             # для выбора тегов при регистрации
PROFILE_TAG_SELECTION = 9           # для изменения тегов при обновлении профиля
PROFILE_UPDATE_SELECTION = 10       # выбор, что обновлять: контакты или теги
WAIT_FOR_EVENTS_CSV = 11            # новое состояние для загрузки CSV с мероприятиями

def get_main_menu_keyboard(role="user"):
    if role == "admin":
        return ReplyKeyboardMarkup([["🏠 Дом Волонтера", "🤖 ИИ Волонтера"],
                                    ["/load_excel", "/set_admin", "/set_moderator"],
                                    ["/delete_user", "/find_user_id"],
                                    ["/find_users_name", "/find_users_email", "/delete_me", "/load_csv", "/load_events_csv"]],
                                   resize_keyboard=True)
    elif role == "moderator":
        return ReplyKeyboardMarkup([["🏠 Дом Волонтера", "🤖 ИИ Волонтера"],
                                    ["/delete_user", "/find_user_id"],
                                    ["/delete_me", "/load_csv", "/load_events_csv"]],
                                   resize_keyboard=True)
    elif role == "guest":
        return ReplyKeyboardMarkup([["🤖 ИИ Помощник", "Мероприятия"], ["Регистрация", "Выход"]],
                                   resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["🏠 Дом Волонтера", "🤖 ИИ Волонтера"]],
                                   resize_keyboard=True)

def get_volunteer_home_keyboard():
    return ReplyKeyboardMarkup([["Регистрация", "Профиль", "Текущие мероприятия"],
                                ["Бонусы", "Информация", "Выход."]],
                               resize_keyboard=True)

def get_profile_menu_keyboard():
    return ReplyKeyboardMarkup([["Информация", "Изменить информацию", "Выход"]],
                               resize_keyboard=True)

class VolunteerBot:
    def __init__(self, token=TOKEN):
        self.token = token
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
        self.db = Database()
        self.application = Application.builder().token(self.token).build()
        self.setup_handlers()

    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", self.start)],
            states={
                MAIN_MENU: [MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонтера|Мероприятия|Регистрация|Выход)$"), self.handle_main_menu)],
                AI_CHAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_ai_chat)],
                VOLUNTEER_HOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_volunteer_home)],
                GUEST_HOME: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_guest_home)],
                GUEST_REGISTRATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_guest_registration)],
                GUEST_TAG_SELECTION: [CallbackQueryHandler(self.handle_tag_selection, pattern="^(tag:|done)$")],
                WAIT_FOR_PROFILE_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_contact_update)],
                PROFILE_UPDATE_SELECTION: [CallbackQueryHandler(self.handle_profile_update_selection, pattern="^(update:)")],
                PROFILE_TAG_SELECTION: [CallbackQueryHandler(self.handle_profile_tag_selection, pattern="^(tag:|done_tags).*")],
                PROFILE_MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_profile_menu)]
            },
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(conv_handler)

        csv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("load_csv", self.load_csv)],
            states={WAIT_FOR_CSV: [MessageHandler(filters.Document.FileExtension("csv"), self.process_csv_document)]},
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(csv_conv_handler)

        # Новый обработчик для загрузки CSV с мероприятиями
        events_csv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("load_events_csv", self.load_events_csv)],
            states={WAIT_FOR_EVENTS_CSV: [MessageHandler(filters.Document.FileExtension("csv"), self.process_events_csv_document)]},
            fallbacks=[CommandHandler("cancel", self.cancel)]
        )
        self.application.add_handler(events_csv_conv_handler)

        self.application.add_handler(CommandHandler("admin", self.admin))
        self.application.add_handler(CommandHandler("load_excel", self.load_excel))
        self.application.add_handler(CommandHandler("set_admin", self.set_admin))
        self.application.add_handler(CommandHandler("set_moderator", self.set_moderator))
        self.application.add_handler(CommandHandler("delete_me", self.delete_self))
        self.application.add_handler(CommandHandler("delete_user", self.admin_delete_user))
        self.application.add_handler(CommandHandler("find_user_id", self.find_user_id))
        self.application.add_handler(CommandHandler("find_users_name", self.find_users_name))
        self.application.add_handler(CommandHandler("find_users_email", self.find_users_email))
        self.application.add_handler(CommandHandler("search_projects_tag", self.search_projects_tag))
        self.application.add_handler(CommandHandler("search_projects_name", self.search_projects_name))
        self.application.add_handler(CommandHandler("search_events_tag", self.search_events_tag))
        self.application.add_handler(CommandHandler("search_events_project", self.search_events_project))
        self.application.add_handler(CommandHandler("ai_query", self.ai_query))

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not user_record:
            role = "admin" if user.id in ADMIN_ID else "guest"
            self.db.save_user(user.id, user.first_name or "", user.last_name or "", "", "", 0, "", role)
            if role == "admin":
                await update.message.reply_markdown("*✅ You are registered! You are an admin.* 🎉")
            else:
                await update.message.reply_markdown("*👋 Добро пожаловать, гость!*")
        else:
            if user_record.get("role") == "user" and user.id in ADMIN_ID:
                self.db.update_user_role(user.id, "admin")
            if user_record.get("role") == "admin":
                await update.message.reply_markdown("*👋 Welcome back, admin!*")
            else:
                await update.message.reply_markdown("*👋 Welcome back!*")
        role = self.db.get_user(user.id).get("role", "guest")
        keyboard = get_main_menu_keyboard(role)
        await update.message.reply_markdown("*📌 Choose a section:*", reply_markup=keyboard)
        return MAIN_MENU

    async def handle_main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        role = self.db.get_user(user.id).get("role", "guest")
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
                events = self.db.get_all_events()
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

    async def handle_guest_home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        return await self.handle_main_menu(update, context)

    async def handle_guest_registration(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        parts = [part.strip() for part in text.split(",")]
        if len(parts) != 3:
            await update.message.reply_markdown("*⚠️ Неверный формат. Введите данные через запятую: Имя, Фамилия, Email*")
            return GUEST_REGISTRATION
        first_name, last_name, email = parts
        user = update.effective_user
        # Сохраняем пользователя без тегов (пока пустая строка)
        self.db.save_user(user.id, first_name, last_name, email, "", 0, "", "user")
        await update.message.reply_markdown("*✅ Вы успешно зарегистрированы!*")
        # Инициируем выбор тегов через инлайн-клавиатуру
        context.user_data['selected_tags'] = []
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("социальное", callback_data="tag:социальное"),
             InlineKeyboardButton("медицина", callback_data="tag:медицина")],
            [InlineKeyboardButton("экология", callback_data="tag:экология"),
             InlineKeyboardButton("культура", callback_data="tag:культура")],
            [InlineKeyboardButton("спорт", callback_data="tag:спорт")],
            [InlineKeyboardButton("Готово", callback_data="done")]
        ])
        await update.message.reply_markdown("*Выберите интересующие вас теги:*", reply_markup=keyboard)
        return GUEST_TAG_SELECTION

    async def handle_tag_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("социальное", callback_data="tag:социальное"),
                 InlineKeyboardButton("медицина", callback_data="tag:медицина")],
                [InlineKeyboardButton("экология", callback_data="tag:экология"),
                 InlineKeyboardButton("культура", callback_data="tag:культура")],
                [InlineKeyboardButton("спорт", callback_data="tag:спорт")],
                [InlineKeyboardButton("Готово", callback_data="done")]
            ])
            await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")
            return GUEST_TAG_SELECTION
        elif data == "done":
            user = update.effective_user
            selected = context.user_data.get('selected_tags', [])
            tags_str = ", ".join(selected)
            current_user = self.db.get_user(user.id)
            if current_user:
                self.db.save_user(
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

    async def handle_ai_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text == "Выход.":
            role = self.db.get_user(update.effective_user.id).get("role", "user")
            keyboard = get_main_menu_keyboard(role)
            await update.message.reply_markdown("Возвращаемся в главное меню:", reply_markup=keyboard)
            return MAIN_MENU
        else:
            from source.agents import ContextRouterAgent
            agent = ContextRouterAgent()
            response = agent.process_query(text, update.effective_user.id)
            await update.message.reply_markdown(response)
            exit_keyboard = ReplyKeyboardMarkup([["Выход."]], resize_keyboard=True)
            return AI_CHAT

    async def handle_volunteer_home(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text == "Выход.":
            role = self.db.get_user(update.effective_user.id).get("role", "user")
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

    async def handle_profile_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        if text == "Информация":
            user = self.db.get_user(update.effective_user.id)
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

    async def handle_profile_update_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        data = query.data
        if data == "update:contact":
            await query.edit_message_text(text="*Введите новые данные в формате: Имя, Фамилия, Email*", parse_mode="Markdown")
            return WAIT_FOR_PROFILE_UPDATE
        elif data == "update:tags":
            user = update.effective_user
            current_user = self.db.get_user(user.id)
            if current_user and current_user.get("tags"):
                context.user_data['selected_tags'] = [tag.strip() for tag in current_user.get("tags", "").split(",") if tag.strip()]
            else:
                context.user_data['selected_tags'] = []
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("социальное", callback_data="tag:социальное"),
                 InlineKeyboardButton("медицина", callback_data="tag:медицина")],
                [InlineKeyboardButton("экология", callback_data="tag:экология"),
                 InlineKeyboardButton("культура", callback_data="tag:культура")],
                [InlineKeyboardButton("спорт", callback_data="tag:спорт")],
                [InlineKeyboardButton("Готово", callback_data="done_tags")]
            ])
            init_text = "*Выберите интересующие вас теги:*\n"
            init_text += "Выбрано: " + ", ".join(context.user_data['selected_tags']) if context.user_data['selected_tags'] else "Ничего не выбрано."
            await query.edit_message_text(text=init_text, reply_markup=keyboard, parse_mode="Markdown")
            return PROFILE_TAG_SELECTION

    async def handle_contact_update(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        text = update.message.text.strip()
        parts = [part.strip() for part in text.split(",")]
        if len(parts) != 3:
            await update.message.reply_markdown("*⚠️ Неверный формат. Введите данные через запятую: Имя, Фамилия, Email*")
            return WAIT_FOR_PROFILE_UPDATE
        first_name, last_name, email = parts
        user = update.effective_user
        current_user = self.db.get_user(user.id)
        if current_user:
            self.db.save_user(
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

    async def handle_profile_tag_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    ("✅ социальное" if "социальное" in selected else "социальное"),
                    callback_data="tag:социальное"
                ),
                    InlineKeyboardButton(
                        ("✅ медицина" if "медицина" in selected else "медицина"),
                        callback_data="tag:медицина"
                    )],
                [InlineKeyboardButton(
                    ("✅ экология" if "экология" in selected else "экология"),
                    callback_data="tag:экология"
                ),
                    InlineKeyboardButton(
                        ("✅ культура" if "культура" in selected else "культура"),
                        callback_data="tag:культура"
                    )],
                [InlineKeyboardButton(
                    ("✅ спорт" if "спорт" in selected else "спорт"),
                    callback_data="tag:спорт"
                )],
                [InlineKeyboardButton("Готово", callback_data="done_tags")]
            ])
            await query.edit_message_text(text=text, reply_markup=keyboard, parse_mode="Markdown")
            return PROFILE_TAG_SELECTION
        elif data == "done_tags":
            user = update.effective_user
            selected = context.user_data.get('selected_tags', [])
            tags_str = ", ".join(selected)
            current_user = self.db.get_user(user.id)
            if current_user:
                self.db.save_user(
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

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_markdown("*↩️ Returning to the main menu.*")
        role = self.db.get_user(update.effective_user.id).get("role", "user")
        keyboard = get_main_menu_keyboard(role)
        await update.message.reply_markdown("Выберите раздел:", reply_markup=keyboard)
        return MAIN_MENU

    async def load_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not (user_record and user_record.get("role") == "admin"):
            await update.message.reply_markdown("*🚫 You do not have access to this command.*")
            return MAIN_MENU
        await update.message.reply_markdown("*📥 Please send a CSV file with data (.csv extension).*")
        return WAIT_FOR_CSV

    async def process_csv_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                    self.db.add_project(name, curator, phone_number, email, description, tags)
                    count += 1
            os.remove(temp_path)
            await update.message.reply_markdown(f"*✅ CSV file processed successfully.* Projects added: _{count}_.")
        except Exception as e:
            self.logger.error(f"CSV load error: {e}")
            await update.message.reply_markdown("*🚫 An error occurred while processing the CSV.*")
        return MAIN_MENU

    async def load_events_csv(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not (user_record and user_record.get("role") == "admin"):
            await update.message.reply_markdown("*🚫 You do not have access to this command.*")
            return MAIN_MENU
        await update.message.reply_markdown("*📥 Please send a CSV file with event data (.csv extension).*")
        return WAIT_FOR_EVENTS_CSV

    async def process_events_csv_document(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
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
                    # Ожидаемые столбцы: "Название", "Дата", "Время", "Локация", "Организатор", "Описание"
                    event_date = row.get("Дата")
                    start_time = row.get("Время")
                    creator = row.get("Организатор")
                    if not event_date or not start_time or not creator:
                        continue
                    name = row.get("Название", "")
                    location = row.get("Локация", "")
                    description = row.get("Описание", "")
                    # Собираем дополнительные сведения в поле tags
                    tags = f"Название: {name}; Локация: {location}; Описание: {description}"
                    # Добавляем запись в таблицу events, project_id оставляем None
                    self.db.add_event_detail(None, event_date, start_time, 0, 5, creator, tags)
                    count += 1
            os.remove(temp_path)
            await update.message.reply_markdown(f"*✅ CSV file processed successfully.* Events added: _{count}_.")
        except Exception as e:
            self.logger.error(f"Events CSV load error: {e}")
            await update.message.reply_markdown("*🚫 An error occurred while processing the events CSV.*")
        return MAIN_MENU

    async def admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if user_record and user_record.get("role") == "admin":
            await update.message.reply_markdown("*👋 Hello, admin!* Available commands:\n• /load_excel - load data from Excel\n• /set_admin <user_id> - assign admin\n• /set_moderator <user_id> - assign moderator\n• /delete_user <user_id> - delete user\n• /find_user_id <user_id> - find user by id\n• /find_users_name <name> - find users by name/surname\n• /find_users_email <email> - find users by email\n• /delete_me - delete your account\n• /ai_query <query> - process query with AI agent\n• /search_projects_tag <tag> - search projects by tag\n• /search_projects_name <name> - search projects by name\n• /search_events_tag <tag> - search events by tag\n• /search_events_project <project name> - search events by project name\n• /load_csv - load projects CSV\n• /load_events_csv - load events CSV")
        else:
            await update.message.reply_markdown("*🚫 You do not have access to admin commands.*")

    async def load_excel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not (user_record and user_record.get("role") == "admin"):
            await update.message.reply_markdown("*🚫 You do not have access to this command.*")
            return
        try:
            workbook = openpyxl.load_workbook("./data/events.xlsx")
            sheet = workbook.active
            count = 0
            for row in sheet.iter_rows(min_row=2, values_only=True):
                name, date, time_value, location, curator, description, code, tags = row
                if not name:
                    continue
                self.db.add_project(name, curator, time_value, location, description, tags)
                count += 1
            await update.message.reply_markdown(f"*✅ Excel file processed successfully.* Projects added: _{count}_.")
        except Exception as e:
            self.logger.error(f"Excel load error: {e}")
            await update.message.reply_markdown("*🚫 An error occurred while processing the Excel file.*")

    async def set_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not (user_record and user_record.get("role") == "admin"):
            await update.message.reply_markdown("*🚫 You do not have access to this command.*")
            return
        try:
            target_user_id = int(context.args[0])
            self.db.update_user_role(target_user_id, "admin")
            await update.message.reply_markdown(f"*✅ User {target_user_id} has been assigned as admin.*")
        except (IndexError, ValueError):
            await update.message.reply_markdown("*⚠️ Usage: /set_admin <user_id>*")

    async def set_moderator(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not (user_record and user_record.get("role") == "admin"):
            await update.message.reply_markdown("*🚫 You do not have access to this command.*")
            return
        try:
            target_user_id = int(context.args[0])
            self.db.update_user_role(target_user_id, "moderator")
            await update.message.reply_markdown(f"*✅ User {target_user_id} has been assigned as moderator.*")
        except (IndexError, ValueError):
            await update.message.reply_markdown("*⚠️ Usage: /set_moderator <user_id>*")

    async def delete_self(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        self.db.delete_user(user.id)
        await update.message.reply_markdown("*✅ Your account has been deleted.* To re-register, use /start.")

    async def admin_delete_user(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        user_record = self.db.get_user(user.id)
        if not (user_record and user_record.get("role") in ["admin", "moderator"]):
            await update.message.reply_markdown("*🚫 You do not have access to this command.*")
            return
        try:
            target_user_id = int(context.args[0])
            self.db.delete_user(target_user_id)
            await update.message.reply_markdown(f"*✅ User {target_user_id} has been deleted.*")
        except (IndexError, ValueError):
            await update.message.reply_markdown("*⚠️ Usage: /delete_user <user_id>*")

    async def find_user_id(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            target_user_id = int(context.args[0])
            user = self.db.find_user_by_id(target_user_id)
            if user is None:
                await update.message.reply_markdown("*❌ User not found.*")
            else:
                await update.message.reply_markdown(f"*👤 User found:*\n{user}")
        except (IndexError, ValueError):
            await update.message.reply_markdown("*⚠️ Usage: /find_user_id <user_id>*")

    async def find_users_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            name = " ".join(context.args)
            users = self.db.find_users_by_name(name)
            if not users:
                await update.message.reply_markdown("*❌ No users found.*")
            else:
                message = "*👥 Users found:*\n"
                for user in users:
                    message += f"ID: {user['id']}, Name: {user['first_name']} {user['last_name']}\n"
                await update.message.reply_markdown(message)
        except Exception:
            await update.message.reply_markdown("*🚫 Error while searching users by name.*")

    async def find_users_email(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            email = " ".join(context.args)
            users = self.db.find_users_by_email(email)
            if not users:
                await update.message.reply_markdown("*❌ No users found.*")
            else:
                message = "*📧 Users found:*\n"
                for user in users:
                    message += f"ID: {user['id']}, Email: {user['email']}\n"
                await update.message.reply_markdown(message)
        except Exception:
            await update.message.reply_markdown("*🚫 Error while searching users by email.*")

    async def search_projects_tag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            tag = " ".join(context.args)
            if not tag:
                await update.message.reply_markdown("*⚠️ Usage: /search_projects_tag <tag>*")
                return
            projects = self.db.search_projects_by_tag(tag)
            if projects:
                message = "*Projects found by tag:*\n"
                for project in projects:
                    message += f"ID: {project['id']}, Name: {project['name']}, Tags: {project['tags']}\n"
                await update.message.reply_markdown(message)
            else:
                await update.message.reply_markdown("*No projects found for this tag.*")
        except Exception:
            await update.message.reply_markdown("*Error while searching projects by tag.*")

    async def search_projects_name(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            name = " ".join(context.args)
            if not name:
                await update.message.reply_markdown("*⚠️ Usage: /search_projects_name <project name>*")
                return
            projects = self.db.search_projects_by_name(name)
            if projects:
                message = "*Projects found by name:*\n"
                for project in projects:
                    message += f"ID: {project['id']}, Name: {project['name']}, Tags: {project['tags']}\n"
                await update.message.reply_markdown(message)
            else:
                await update.message.reply_markdown("*No projects found for this name.*")
        except Exception:
            await update.message.reply_markdown("*Error while searching projects by name.*")

    async def search_events_tag(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            tag = " ".join(context.args)
            if not tag:
                await update.message.reply_markdown("*⚠️ Usage: /search_events_tag <tag>*")
                return
            events = self.db.search_events_by_tag(tag)
            if events:
                message = "*Events found by tag:*\n"
                for event in events:
                    message += f"ID: {event['id']}, Project ID: {event['project_id']}, Date: {event['event_date']}, Tags: {event['tags']}\n"
                await update.message.reply_markdown(message)
            else:
                await update.message.reply_markdown("*No events found for this tag.*")
        except Exception:
            await update.message.reply_markdown("*Error while searching events by tag.*")

    async def search_events_project(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            project_name = " ".join(context.args)
            if not project_name:
                await update.message.reply_markdown("*⚠️ Usage: /search_events_project <project name>*")
                return
            events = self.db.search_events_by_project_name(project_name)
            if events:
                message = "*Events found for project:*\n"
                for event in events:
                    message += f"ID: {event['id']}, Date: {event['event_date']}, Start Time: {event['start_time']}, Tags: {event['tags']}\n"
                await update.message.reply_markdown(message)
            else:
                await update.message.reply_markdown("*No events found for this project name.*")
        except Exception:
            await update.message.reply_markdown("*Error while searching events by project name.*")

    async def ai_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = " ".join(context.args)
        if not query:
            await update.message.reply_markdown("*⚠️ Usage: /ai_query <query>*")
            return
        agent = RecommendationAgent()
        response = agent.recommend_events(update.effective_user.id)
        prompt = (
            f"Evaluate the following recommendations for the user based on their preferences:\n"
            f"{response}\nProvide a final evaluation and additional recommendations if necessary."
        )
        result = agent.process_query(prompt, update.effective_user.id)
        await update.message.reply_markdown(result)

    def run(self):
        self.logger.info("Bot is running.")
        self.application.run_polling()

if __name__ == "__main__":
    bot = VolunteerBot()
    bot.run()
