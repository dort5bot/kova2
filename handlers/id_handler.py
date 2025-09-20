#handlers/id_handler.py
"""
Böylece /admin ve /id komutları artık

"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command  # filtreyi import et
from config import config

router = Router()

@router.message(Command("admin"))
async def admin_command(message: Message):
    user_id = message.from_user.id
    print(f"Gelen kullanıcı ID: {user_id}")
    print(f"Yetkili ID listesi: {config.ADMIN_CHAT_IDS}")
    if user_id not in config.ADMIN_CHAT_IDS:
        await message.reply("❌ Bu komutu kullanma yetkiniz yok.")
        return

    await message.reply("✅ Admin paneline hoş geldiniz.")

@router.message(Command("id"))
async def id_command(message: Message):
    user_id = message.from_user.id
    await message.reply(f"Senin ID: {user_id}\nYetkili ID listesi: {config.ADMIN_CHAT_IDS}")
