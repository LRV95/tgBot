import logging
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler, CallbackContext
from config import TOKEN, ADMIN_ID
from bot.handlers.common import start, cancel

from bot.states import (MAIN_MENU, WAIT_FOR_CSV, AI_CHAT, VOLUNTEER_HOME, GUEST_HOME, PROFILE_MENU,
                        WAIT_FOR_PROFILE_UPDATE, REGISTRATION_TAG_SELECTION, PROFILE_TAG_SELECTION,
                        WAIT_FOR_EVENTS_CSV, REGISTRATION_CITY_SELECTION,
                        PROFILE_CITY_SELECTION, EVENT_DETAILS, MODERATION_MENU, MODERATOR_EVENT_NAME,
                        MODERATOR_EVENT_DATE, MODERATOR_EVENT_TIME, MODERATOR_EVENT_CITY,
                        MODERATOR_EVENT_DESCRIPTION, MODERATOR_EVENT_CONFIRMATION, REDEEM_CODE,
                        MODERATOR_SEARCH_REGISTERED_USERS, MODERATOR_EVENT_CODE, WAIT_FOR_EMPLOYEE_NUMBER)

from bot.handlers.admin import (admin_command, load_excel, set_admin, set_moderator, delete_user, find_user_id,
                                find_users_name, find_users_email, load_projects_csv, process_csv_document,
                                load_events_csv, process_events_csv_document, moderation_menu,
                                handle_moderation_menu_selection, moderator_create_event_start, moderator_handle_event_name,
                                moderator_handle_event_date, moderator_handle_event_time, moderator_handle_event_city,
                                moderator_handle_event_description, moderator_confirm_event, moderator_view_events,
                                moderator_delete_event, moderator_handle_delete_event_callback, moderator_handle_search_event_users,
                                moderator_handle_event_code)

from bot.handlers.user import (handle_main_menu, handle_ai_chat, handle_volunteer_home, handle_registration,
                               handle_registration_tag_selection, handle_profile_menu, handle_contact_update,
                               handle_profile_tag_selection, handle_events_callbacks,
                               handle_registration_city_selection, handle_events, handle_profile_city_selection,
                               handle_code_redemption, handle_employee_number)

def admin_required(func):
    def wrapper(update: Update, context: CallbackContext):
        user_id = update.effective_user.id
        if user_id not in ADMIN_ID:
            if update.message:
                update.message.reply_text("У вас недостаточно прав для выполнения этой команды.")
            elif update.effective_message:
                update.effective_message.reply_text("У вас недостаточно прав для выполнения этой команды.")
            return
        return func(update, context)
    return wrapper

# Универсальный обработчик для возврата в главное меню
def global_main_menu_handler(update: Update, context: CallbackContext):
    return handle_main_menu(update, context)

class VolunteerBot:
    def __init__(self, token=TOKEN):
        self.token = token
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO,
                            handlers=[logging.FileHandler("bot.log"), logging.StreamHandler(sys.stdout)])
        try:
            self.application = Application.builder().token(self.token).build()
            self.setup_handlers()
        except Exception as e:
            self.logger.critical(f"Критическая ошибка при инициализации бота: {e}")
            sys.exit(1)

    def setup_handlers(self):
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                MAIN_MENU: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
                ],
                AI_CHAT: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat)
                ],
                VOLUNTEER_HOME: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_volunteer_home)
                ],
                # Добавлен обработчик для текстового сообщения "Выход" в состоянии GUEST_HOME
                GUEST_HOME: [
                    MessageHandler(filters.Regex("^(Выход)$"), global_main_menu_handler),
                    CallbackQueryHandler(handle_events_callbacks, pattern="^(register_event:.*|events_next:.*|events_prev:.*|back_to_menu|view_event:.*|share_event:.*|show_filters|filter_tag:.*|back_to_events|unregister_event:.*)$")
                ],
                WAIT_FOR_EMPLOYEE_NUMBER: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employee_number)
                ],
                REGISTRATION_CITY_SELECTION: [
                    CallbackQueryHandler(handle_registration_city_selection, pattern="^(city:.*|city_next:.*|city_prev:.*|done_cities)$")
                ],
                REGISTRATION_TAG_SELECTION: [
                    CallbackQueryHandler(handle_registration_tag_selection, pattern="^(tag:.*|done_tags)$")
                ],
                WAIT_FOR_PROFILE_UPDATE: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_update)
                ],
                PROFILE_TAG_SELECTION: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_tag_selection)
                ],
                PROFILE_MENU: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_menu)
                ],
                PROFILE_CITY_SELECTION: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_city_selection)
                ],
                MODERATION_MENU: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_moderation_menu_selection)
                ],
                EVENT_DETAILS: [
                    CallbackQueryHandler(handle_events_callbacks, pattern="^(register_event:.*|unregister_event:.*|back_to_events|share_event:.*)$")
                ],
                REDEEM_CODE: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_redemption)
                ],
                MODERATOR_EVENT_NAME: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_name)
                ],
                MODERATOR_EVENT_DATE: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_date)
                ],
                MODERATOR_EVENT_TIME: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_time)
                ],
                MODERATOR_EVENT_CITY: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_city)
                ],
                MODERATOR_SEARCH_REGISTERED_USERS: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_search_event_users)
                ],
                MODERATOR_EVENT_DESCRIPTION: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_description)
                ],
                MODERATOR_EVENT_CONFIRMATION: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_confirm_event)
                ],
                MODERATOR_EVENT_CODE: [
                    MessageHandler(filters.Regex("^(🏠 Дом Волонтера|🤖 ИИ Волонера)$"), global_main_menu_handler),
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_code)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(conv_handler)
        csv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("load_projects_csv", load_projects_csv)],
            states={WAIT_FOR_CSV: [MessageHandler(filters.Document.FileExtension("csv"), process_csv_document)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(csv_conv_handler)
        events_csv_conv_handler = ConversationHandler(
            entry_points=[CommandHandler("load_events_csv", load_events_csv)],
            states={WAIT_FOR_EVENTS_CSV: [MessageHandler(filters.Document.FileExtension("csv"), process_events_csv_document)]},
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(events_csv_conv_handler)
        self.application.add_handler(CommandHandler("admin", admin_required(admin_command)))
        self.application.add_handler(CommandHandler("load_excel", admin_required(load_excel)))
        self.application.add_handler(CommandHandler("set_admin", admin_required(set_admin)))
        self.application.add_handler(CommandHandler("set_moderator", admin_required(set_moderator)))
        self.application.add_handler(CommandHandler("delete_user", admin_required(delete_user)))
        self.application.add_handler(CommandHandler("find_user_id", admin_required(find_user_id)))
        self.application.add_handler(CommandHandler("find_users_name", admin_required(find_users_name)))
        self.application.add_handler(CommandHandler("find_users_email", admin_required(find_users_email)))

    def run(self):
        try:
            for sig in (signal.SIGTERM, signal.SIGINT):
                self.application.add_handler(CommandHandler(str(sig), lambda u, c: self.shutdown(sig)))
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
