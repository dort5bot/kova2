# handlers/json_handler.py
"""
# aiofiles


"""
import os
import tempfile
import logging
from aiogram import F, Router
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from utils.json_processing import process_excel_to_json

logger = logging.getLogger(__name__)
router = Router()

class JsonProcessingState(StatesGroup):
    waiting_for_excel = State()

@router.message(Command("js"))
async def handle_json_command(message: Message, state: FSMContext):
    """
    /js komutunu işler ve Excel dosyası bekler
    """
    await message.answer("📊 Lütfen işlemek istediğiniz Excel dosyasını gönderin...")
    await state.set_state(JsonProcessingState.waiting_for_excel)

@router.message(JsonProcessingState.waiting_for_excel, F.document)
async def handle_excel_file(message: Message, state: FSMContext):
    """
    Excel dosyasını işler
    """
    if not message.document.file_name.endswith(('.xlsx', '.xls')):
        await message.answer("❌ Sadece Excel dosyaları (.xlsx, .xls) desteklenmektedir.")
        await state.clear()
        return

    try:
        # Dosyayı indir
        file_info = await message.bot.get_file(message.document.file_id)
        downloaded_file = await message.bot.download_file(file_info.file_path)

        # Geçici dosya oluştur
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx') as tmp_file:
            tmp_file.write(downloaded_file.read())
            temp_file_path = tmp_file.name

        # İşlemi başlat
        await message.answer("⏳ Excel dosyası işleniyor...")

        # JSON işleme
        json_file_path = await process_excel_to_json(temp_file_path)

        if json_file_path and os.path.exists(json_file_path):
            # JSON dosyasını oku ve gönder
            with open(json_file_path, 'rb') as json_file:
                json_data = json_file.read()
            
            # JSON dosyasını gönder
            input_file = BufferedInputFile(json_data, filename="groups.json")
            await message.answer_document(input_file, caption="✅ Grup verileri başarıyla oluşturuldu!")
            
            # Geçici dosyayı sil
            os.unlink(temp_file_path)
            logger.info(f"Geçici Excel dosyası silindi: {temp_file_path}")
        else:
            await message.answer("❌ JSON dosyası oluşturulamadı.")
            if os.path.exists(temp_file_path):
                os.unlink(temp_file_path)

    except Exception as e:
        logger.error(f"JSON işleme hatası: {str(e)}", exc_info=True)
        await message.answer(f"❌ Hata oluştu: {str(e)}")
        
        # Hata durumunda geçici dosyayı temizle
        if 'temp_file_path' in locals() and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
    
    finally:
        await state.clear()

@router.message(JsonProcessingState.waiting_for_excel)
async def handle_wrong_file_type(message: Message, state: FSMContext):
    """
    Excel dosyası dışında bir şey gönderilirse
    """
    await message.answer("❌ Lütfen sadece Excel dosyası (.xlsx, .xls) gönderin.")
    await state.clear()