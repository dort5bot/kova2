#buttons/button_handler.py
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command


from .kova_button import get_kova_keyboard
from .js_button import get_js_keyboard
from .mail_button import get_mail_keyboard

router = Router()

@router.callback_query(F.data == "process_command")
async def process_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    # /process komutunu tetikleme mantığı buraya gelebilir
    # Veya doğrudan upload_handler'daki fonksiyonu çağırabilirsiniz
    await callback_query.message.answer("📤 Dosya yükleme işlemi başlat... /process")

@router.callback_query(F.data == "js_command")
async def js_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("📊 JSON işleme tıkla... /js")

@router.callback_query(F.data == "send_test_email_command")
async def mail_callback_handler(callback_query: CallbackQuery):
    await callback_query.answer()
    await callback_query.message.answer("📧 Test maili tıkla... /send_test_email")

# Butonları gösteren komutlar
@router.message(Command("b"))     ##@router.message(Command("buttons"))
async def show_buttons_command(message: Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Dosya Yükle", callback_data="process_command")],
        [InlineKeyboardButton(text="📊 JSON İşleme", callback_data="js_command")],
        [InlineKeyboardButton(text="📧 Test Mail", callback_data="send_test_email_command")]
    ])
    await message.answer("İşlem seçin:", reply_markup=keyboard)