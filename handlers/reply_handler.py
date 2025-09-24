# handlers/reply_handler.py
"""
Reply Keyboard → Kullanıcı dostu arayüz:
Temizle → /clear
Kova → /process
Bana → /bana
JSON yap → /js
Komutlar → /dar (bana komutunu ekle, tümünü bu maile atar)

"""

import logging
from aiogram import Router
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext

logger = logging.getLogger(__name__)
router = Router()

#iptal
class ReplyKeyboardSingleton:
    """
    Singleton sınıfı: sadece bir tane ReplyKeyboard üretir.
    """

    _instance: ReplyKeyboardMarkup | None = None

    @classmethod
    def get_keyboard(cls) -> ReplyKeyboardMarkup:
        """Tekil ReplyKeyboard örneğini döndürür."""
        if cls._instance is None:
            logger.debug("ReplyKeyboard oluşturuluyor...")
            cls._instance = ReplyKeyboardMarkup(
                keyboard=[
                    [KeyboardButton(text="Temizle"), KeyboardButton(text="Kova"), KeyboardButton(text="TEK")],
                    [KeyboardButton(text="iptal"),KeyboardButton(text="JSON yap"), KeyboardButton(text="Komutlar")],
                ],

                resize_keyboard=True,
                one_time_keyboard=False,
                input_field_placeholder="Bir işlem seçin...",
            )
        return cls._instance


async def show_reply_keyboard(message: Message, title: str) -> None:
    """
    Ortak reply keyboard gösterici.
    """
    keyboard = ReplyKeyboardSingleton.get_keyboard()
    await message.answer(
        f"{title}\n\nAşağıdaki seçeneklerden birini seçin veya Excel dosyası gönderin:",
        reply_markup=keyboard,
    )


# ---------------------------------------------------
# /start ve /r komutları
# ---------------------------------------------------

@router.message(Command("start"))
async def cmd_start_with_keyboard(message: Message) -> None:
    """
    /start komutu → karşılama mesajı + reply keyboard
    """
    logger.info("Start komutu çalıştı: %s", message.from_user.id)
    await show_reply_keyboard(message, "📊 Excel İşleme Botuna Hoşgeldiniz!")


@router.message(Command("r"))
async def cmd_reply_keyboard(message: Message) -> None:
    """
    /r komutu → reply keyboard menüsü
    """
    logger.info("Reply keyboard menüsü çağrıldı: %s", message.from_user.id)
    await show_reply_keyboard(message, "📋 Hızlı Erişim Menüsü")


# ---------------------------------------------------
# Tuşların işlemleri
# ---------------------------------------------------

#@router.message(lambda m: m.text == "Temizle")
@router.message(lambda m: m.text and m.text == "Temizle")
async def handle_clear(message: Message, state: FSMContext) -> None:
    """
    Reply keyboard → Temizle butonu (/clear)
    """
    logger.info("Temizle komutu çalıştırılıyor: %s", message.from_user.id)
    from handlers.file_handler import clear_all

    await message.answer("🧹 Temizlik başlatılıyor...")
    await clear_all(message)


# İptal butonu handler'ı ekleyin
@router.message(lambda m: m.text and m.text == "iptal")
async def handle_cancel_button(message: Message, state: FSMContext):
    """Reply keyboard'dan iptal işlemi"""
    current_state = await state.get_state()
    
    if current_state is None:
        await message.answer("ℹ️ İptal edilecek aktif işlem yok.")
        return
    
    await state.clear()
    await message.answer(
        "❌ İşlem iptal edildi.\n"
        "Yeni bir işlem başlatmak için menüden seçim yapabilirsiniz.",
        reply_markup=ReplyKeyboardSingleton.get_keyboard()
    )


@router.message(lambda m: m.text == "Kova")
async def handle_process(message: Message, state: FSMContext) -> None:
    """
    Reply keyboard → İşle butonu (/process)
    """
    logger.info("İşle komutu çalıştırılıyor: %s", message.from_user.id)
    from handlers.upload_handler import cmd_process

    await message.answer("⚙️ İşlem başlatılıyor...")
    await cmd_process(message, state)



# TEK butonu handler'ı ekle
@router.message(lambda m: m.text == "TEK")
async def handle_tek(message: Message, state: FSMContext):
    """Reply keyboard → TEK butonu (/tek)"""
    from handlers.tek_handler import cmd_tek
    await message.answer("⚙️ TEK işlem başlatılıyor...")
    await cmd_tek(message, state)

@router.message(lambda m: m.text == "JSON yap")
async def handle_create_json(message: Message, state: FSMContext) -> None:
    """
    Reply keyboard → JSON oluştur butonu (/js)
    """
    logger.info("JSON oluşturma komutu çalıştırılıyor: %s", message.from_user.id)
    from handlers.json_handler import handle_json_command

    await message.answer("📊 JSON oluşturma başlatılıyor...")
    await handle_json_command(message, state)


@router.message(lambda m: m.text == "Komutlar")
async def handle_show_commands(message: Message, state: FSMContext) -> None:
    """
    Reply keyboard → Komut listesi butonu (/dar)
    """
    logger.info("Komut listesi komutu çağrıldı: %s", message.from_user.id)
    from handlers.dar_handler import scan_handlers_for_commands

    scanned = scan_handlers_for_commands()
    lines = [f"{cmd} → {desc}" for cmd, desc in sorted(scanned.items())]
    text = "\n".join(lines) if lines else "❌ Komut bulunamadı."

    await message.answer(f"<pre>{text}</pre>", parse_mode="HTML")

