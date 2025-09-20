#buttons/mail_button.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_mail_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📧 Test Mail Gönder (/send_test_email)",
            callback_data="send_test_email_command"
        )
    )
    return builder.as_markup()
