from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from utils.excel_cleaner import clean_excel_headers
from utils.excel_splitter import split_excel_by_groups
from utils.validator import validate_excel_file
from utils.reporter import generate_processing_report
from jobs.process_excel import process_excel_task_with_zip

from utils.logger import logger

router = Router()

class ProcessingStates(StatesGroup):
    waiting_for_file = State()

@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(
        "📊 Excel İşleme Botuna Hoşgeldiniz!\n\n"
        "Lütfen işlemek istediğiniz Excel dosyasını gönderin. "
        "Dosyada 1.satırda 'TARİH' ve 'İL' sütunları bulunmalıdır."
    )

@router.message(Command("process"))
async def cmd_process(message: Message, state: FSMContext):
    await state.set_state(ProcessingStates.waiting_for_file)
    await message.answer(
        "📊 PROCESS MODU\n\n"
        "Lütfen Excel dosyasını gönderin.\n"
        "• Dosya gruplara ayrılacak\n"
        "• Tüm çıktılar ZIP olarak kişisel maile gönderilecek\n"
        f"• Alıcı: {config.PERSONAL_EMAIL}"
    )

@router.message(ProcessingStates.waiting_for_file, F.document)
async def handle_excel_upload(message: Message, state: FSMContext):
    try:
        file_id = message.document.file_id
        file_name = message.document.file_name
        
        if not file_name.endswith(('.xlsx', '.xls')):
            await message.answer("❌ Lütfen Excel dosyası (.xlsx veya .xls) gönderin.")
            await state.clear()
            return
        
        # Dosyayı indir
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = config.INPUT_DIR / file_name
        
        await bot.download_file(file.file_path, file_path)
        
        # Doğrulama
        #validation_result = validate_excel_file(file_path)
        # Doğrulama kısmını düzeltin:
        validation_result = validate_excel_file(str(file_path))  # Path yerine str
        if not validation_result["valid"]:
            await message.answer(f"❌ {validation_result['message']}")
            await state.clear()
            file_path.unlink()  # Geçici dosyayı sil
            return
        
        await message.answer("⏳ Dosya işleniyor, lütfen bekleyin...")
        
        # /process komutu için ZIP gönderimli işlem
        task_result = await process_excel_task_with_zip(file_path, message.from_user.id)
        
        if task_result["success"]:
            # Rapor oluştur
            report = generate_processing_report(task_result)
            await message.answer(report)
            
        else:
            await message.answer(f"❌ İşlem sırasında hata oluştu: {task_result['error']}")
        
    except Exception as e:
        logger.error(f"Dosya işleme hatası: {e}")
        await message.answer("❌ Dosya işlenirken bir hata oluştu.")
    finally:
        await state.clear()

@router.message(ProcessingStates.waiting_for_file)
async def handle_wrong_file_type(message: Message):
    await message.answer("❌ Lütfen bir Excel dosyası gönderin.")