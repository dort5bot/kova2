# handlers/cancel_handler.py dosyası oluşturun
"""
işlem iptal komutunu
/cancel, /iptal, /stop))
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from handlers.reply_handler import show_reply_keyboard

router = Router()

@router.message(Command("cancel", "iptal", "stop"))
async def cmd_cancel(message: Message, state: FSMContext):
    """Mevcut işlemi iptal eder"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("ℹ️ İptal edilecek aktif işlem yok.")
        return
    
    # State'i temizle
    await state.clear()
    

    # ✅ Tüm await çağrıları fonksiyonun içinde olacak
    await message.answer("❌ İşlem iptal edildi.")
    await show_reply_keyboard(message, "📋 Ana menüye döndünüz.")
