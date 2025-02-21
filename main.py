"""Основной файл бота."""

import logging
import signal
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    CallbackQueryHandler
)

from config import TOKEN
from bot.states import (
    MAIN_MENU,
    WAIT_FOR_CSV,
    AI_CHAT,
    VOLUNTEER_HOME,
    GUEST_HOME,
    GUEST_REGISTRATION,
    GUEST_TAG_SELECTION,
    PROFILE_MENU,
    WAIT_FOR_PROFILE_UPDATE,
    PROFILE_TAG_SELECTION,
    PROFILE_UPDATE_SELECTION,
    WAIT_FOR_EVENTS_CSV
)
from bot.handlers.common import start, cancel
from bot.handlers.admin import (
    admin_command,
    load_excel,
    set_admin,
    set_moderator,
    delete_user,
    find_user_id,
    find_users_name,
    find_users_email,
    load_csv,
    process_csv_document,
    load_events_csv,
    process_events_csv_document
)
from bot.handlers.user import (
    handle_main_menu,
    handle_ai_chat,
    handle_volunteer_home,
    handle_guest_registration,
    handle_tag_selection,
    handle_profile_menu,
    handle_profile_update_selection,
    handle_contact_update,
    handle_profile_tag_selection
)

class VolunteerBot:
    """Основной класс бота."""
    
    def __init__(self, token=TOKEN):
        """Инициализация бота."""
        self.token = token
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            level=logging.INFO,
            handlers=[
                logging.FileHandler("bot.log"),
                logging.StreamHandler(sys.stdout)
            ]
        )
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
        except Exception as e:
            self.logger.critical(f"Критическая ошибка при инициализации бота: {e}")
            sys.exit(1)

    def setup_handlers(self):
        """Настройка обработчиков команд."""
        # Основной обработчик диалога
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                MAIN_MENU: [
                    MessageHandler(
                        filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Помощник|🤖 ИИ Волонтера|Мероприятия|Регистрация|Выход)$"),
                        handle_main_menu
                    )
                ],
                AI_CHAT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat)
                ],
                VOLUNTEER_HOME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_volunteer_home)
                ],
                GUEST_HOME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
                ],
                GUEST_REGISTRATION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_guest_registration)
                ],
                GUEST_TAG_SELECTION: [
                    CallbackQueryHandler(handle_tag_selection, pattern="^(tag:|done)$")
                ],
                WAIT_FOR_PROFILE_UPDATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_update)
                ],
                PROFILE_UPDATE_SELECTION: [
                    CallbackQueryHandler(handle_profile_update_selection, pattern="^(update:)")
                ],
                PROFILE_TAG_SELECTION: [
                    CallbackQueryHandler(handle_profile_tag_selection, pattern="^(tag:|done_tags).*")
                ],
                PROFILE_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_menu)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(conv_handler)

        # Обработчик загрузки CSV с проектами
        csv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("load_csv", load_csv)],
            states={
                WAIT_FOR_CSV: [
                    MessageHandler(filters.Document.FileExtension("csv"), process_csv_document)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(csv_conv_handler)

        # Обработчик загрузки CSV с мероприятиями
        events_csv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("load_events_csv", load_events_csv)],
            states={
                WAIT_FOR_EVENTS_CSV: [
                    MessageHandler(filters.Document.FileExtension("csv"), process_events_csv_document)
                ]
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(events_csv_conv_handler)

        # Административные команды
        self.application.add_handler(CommandHandler("admin", admin_command))
        self.application.add_handler(CommandHandler("load_excel", load_excel))
        self.application.add_handler(CommandHandler("set_admin", set_admin))
        self.application.add_handler(CommandHandler("set_moderator", set_moderator))
        self.application.add_handler(CommandHandler("delete_user", delete_user))
        self.application.add_handler(CommandHandler("find_user_id", find_user_id))
        self.application.add_handler(CommandHandler("find_users_name", find_users_name))
        self.application.add_handler(CommandHandler("find_users_email", find_users_email))

    def run(self):
        """Запуск бота."""
        try:
            # Регистрируем обработчики сигналов
            for sig in (signal.SIGTERM, signal.SIGINT):
                self.application.add_handler(
                    CommandHandler(str(sig), lambda u, c: self.shutdown(sig))
                )
            
            self.logger.info("Бот запущен и готов к работе")
            self.application.run_polling(allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            self.logger.critical(f"Критическая ошибка при работе бота: {e}")
            self.shutdown()

if __name__ == "__main__":
    try:
        bot = VolunteerBot()
        bot.run()
    except Exception as e:
        logging.critical(f"Необработанная ошибка: {e}")
        sys.exit(1)
