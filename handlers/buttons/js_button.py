#buttons/js_button.py
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_js_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="📊 JSON İşleme (/js)",
            callback_data="js_command"
        )
    )
    return builder.as_markup()