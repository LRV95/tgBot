import logging
import signal
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ConversationHandler, filters, CallbackQueryHandler, CallbackContext
from config import TOKEN, ADMIN_ID
from bot.handlers.common import start, cancel, check_password, handle_successful_auth

from bot.states import (ADMIN_MENU, MAIN_MENU, MOD_EVENT_TAGS, EVENT_CSV_IMPORT, AI_CHAT, 
                        VOLUNTEER_DASHBOARD, GUEST_DASHBOARD, PROFILE_MENU,
                        PROFILE_UPDATE_NAME, REGISTRATION_TAG_SELECT, PROFILE_TAG_SELECT,
                        EVENT_CSV_UPLOAD, REGISTRATION_CITY_SELECT,
                        PROFILE_CITY_SELECT, EVENT_DETAILS, MOD_MENU, MOD_EVENT_NAME,
                        MOD_EVENT_DATE, MOD_EVENT_TIME, MOD_EVENT_CITY,
                        MOD_EVENT_DESCRIPTION, MOD_EVENT_CONFIRM, EVENT_CODE_REDEEM,
                        MOD_EVENT_USERS, MOD_EVENT_CODE, PROFILE_EMPLOYEE_NUMBER,
                        MOD_EVENT_CREATOR, MOD_EVENT_POINTS, ADMIN_SET_ADMIN,
                        ADMIN_SET_MODERATOR, ADMIN_DELETE_USER, ADMIN_FIND_USER_ID, ADMIN_FIND_USER_NAME,
                        MOD_EVENT_DELETE, PASSWORD_CHECK, CSV_EXPORT_MENU, EVENT_REPORT_CREATE,
                        EVENT_REPORT_PARTICIPANTS, EVENT_REPORT_PHOTOS, EVENT_REPORT_SUMMARY,
                        EVENT_REPORT_FEEDBACK, PROFILE_EMPLOYEE_NUMBER_UPDATE, MOD_EVENT_EDIT_SELECT,
                        MOD_EVENT_EDIT_FIELD, MOD_EVENT_EDIT_VALUE)

from bot.handlers.admin import (admin_command, handle_admin_id, handle_events_csv, handle_moderator_id, handle_delete_user_id, handle_find_user_id, handle_find_user_name, moderator_handle_event_creator, moderator_handle_event_tags, set_admin, set_moderator, delete_user, find_user_id,
                                find_users_name,
                                handle_moderation_menu_selection, moderator_create_event_start, moderator_handle_event_name,
                                moderator_handle_event_date, moderator_handle_event_time, moderator_handle_event_city,
                                moderator_handle_event_description, moderator_confirm_event, moderator_view_events,
                                moderator_delete_event, moderator_handle_delete_event_callback, moderator_handle_search_event_users,
                                moderator_handle_event_code, moderator_handle_event_participation_points, handle_admin_menu_selection,
                                handle_event_delete, handle_csv_export_menu_selection, handle_event_report_create,
                                create_event_report, handle_report_participants, handle_report_photos,
                                handle_report_summary, handle_report_feedback, view_event_report, handle_event_edit_value,
                                handle_event_edit_field, handle_event_edit_select)

from bot.handlers.user import (handle_event_details, handle_main_menu, handle_ai_chat, handle_volunteer_home, handle_registration,
                               handle_registration_tag_selection, handle_profile_menu, handle_contact_update,
                               handle_profile_tag_selection, handle_events_callbacks,
                               handle_registration_city_selection, handle_events, handle_profile_city_selection,
                               handle_code_redemption, handle_employee_number, handle_employee_number_update)

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
        
        logging.basicConfig(
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
            level=logging.INFO,
            handlers=[
                logging.FileHandler("bot.log", encoding='utf-8'),
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
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start)],
            states={
                PASSWORD_CHECK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, check_password)
                ],
                MAIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_main_menu)
                ],
                AI_CHAT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_ai_chat)
                ],
                VOLUNTEER_DASHBOARD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_volunteer_home)
                ],
                GUEST_DASHBOARD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_events_callbacks)
                ],
                EVENT_DETAILS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_details)
                ],
                PROFILE_EMPLOYEE_NUMBER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employee_number)
                ],
                REGISTRATION_CITY_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration_city_selection)
                ],
                REGISTRATION_TAG_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_registration_tag_selection)
                ],
                PROFILE_UPDATE_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_update)
                ],
                PROFILE_TAG_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_tag_selection)
                ],
                PROFILE_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_menu)
                ],
                PROFILE_CITY_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_profile_city_selection)
                ],
                MOD_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_moderation_menu_selection)
                ],
                ADMIN_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_menu_selection)
                ],
                ADMIN_SET_ADMIN: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_id)
                ],
                ADMIN_SET_MODERATOR: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_moderator_id)
                ],
                ADMIN_DELETE_USER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_delete_user_id)
                ],
                ADMIN_FIND_USER_ID: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_find_user_id)
                ],
                ADMIN_FIND_USER_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_find_user_name)
                ],
                EVENT_CSV_UPLOAD: [
                    MessageHandler(filters.Document.FileExtension("csv"), handle_events_csv)
                ],
                EVENT_CODE_REDEEM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_code_redemption)
                ],
                MOD_EVENT_NAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_name)
                ],
                MOD_EVENT_DATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_date)
                ],
                MOD_EVENT_TIME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_time)
                ],
                MOD_EVENT_CITY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_city)
                ],
                MOD_EVENT_CREATOR: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_creator)
                ],
                MOD_EVENT_DESCRIPTION: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_description)
                ],
                MOD_EVENT_POINTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_participation_points)
                ],
                MOD_EVENT_TAGS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_tags)
                ],
                MOD_EVENT_CODE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_event_code)
                ],
                MOD_EVENT_USERS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_handle_search_event_users)
                ],
                MOD_EVENT_CONFIRM: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, moderator_confirm_event)
                ],
                MOD_EVENT_DELETE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_delete)
                ],
                CSV_EXPORT_MENU: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_csv_export_menu_selection)
                ],
                EVENT_REPORT_CREATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_report_create)
                ],
                EVENT_REPORT_PARTICIPANTS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_participants)
                ],
                EVENT_REPORT_PHOTOS: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_photos)
                ],
                EVENT_REPORT_SUMMARY: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_summary)
                ],
                EVENT_REPORT_FEEDBACK: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_report_feedback)
                ],
                PROFILE_EMPLOYEE_NUMBER: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employee_number)
                ],
                PROFILE_EMPLOYEE_NUMBER_UPDATE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_employee_number_update)
                ],
                MOD_EVENT_EDIT_SELECT: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_edit_select)
                ],
                MOD_EVENT_EDIT_FIELD: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_edit_field)
                ],
                MOD_EVENT_EDIT_VALUE: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_event_edit_value)
                ],
            },
            fallbacks=[CommandHandler("cancel", cancel)]
        )
        self.application.add_handler(conv_handler)
        
        self.application.add_handler(CommandHandler("admin", admin_required(admin_command)))
        self.application.add_handler(CommandHandler("set_admin", admin_required(set_admin)))
        self.application.add_handler(CommandHandler("set_moderator", admin_required(set_moderator)))
        self.application.add_handler(CommandHandler("delete_user", admin_required(delete_user)))
        self.application.add_handler(CommandHandler("find_user_id", admin_required(find_user_id)))
        self.application.add_handler(CommandHandler("find_users_name", admin_required(find_users_name)))

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
