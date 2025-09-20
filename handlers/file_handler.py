# handlers/file_handler.py
"""
/files o → Output dosyalarını zip olarak indirir
/files l → Log dosyalarını zip olarak indirir
/clear → Input, Output ve temp dosyalarını temizler
/clear log → Sadece log dosyalarını temizler

"""
# handlers/file_handler.py
import os
import shutil
import zipfile
import tempfile
from pathlib import Path
from aiogram import Router, F
from aiogram.types import Message, FSInputFile, CallbackQuery
from aiogram.filters import Command
from config import config
from utils.logger import logger

router = Router()

@router.message(Command("files"))
async def cmd_files(message: Message):
    """Dosya yönetimi komutları"""
    args = message.text.strip().split()[1:]
    mode = args[0].lower() if args else ""
    
    if mode == "o":  # Output dosyalarını indir
        await download_output_files(message)
    elif mode == "l":  # Log dosyalarını indir
        await download_log_files(message)
    else:
        await message.answer(
            "📁 Dosya Yönetimi Komutları:\n\n"
            "/files o → Output dosyalarını indir\n"
            "/files l → Log dosyalarını indir"
        )

@router.message(Command("clear"))
async def cmd_clear(message: Message):
    """Temizlik komutları"""
    args = message.text.strip().split()[1:]
    mode = args[0].lower() if args else ""
    
    if mode == "log":  # Logları temizle
        await clear_logs(message)
    else:  # Output ve Input'u temizle
        await clear_all(message)

async def download_output_files(message: Message):
    """Output dosyalarını zip olarak indir"""
    try:
        if not config.OUTPUT_DIR.exists() or not any(config.OUTPUT_DIR.iterdir()):
            await message.answer("❌ Output klasörü boş veya mevcut değil.")
            return
        
        # Zip dosyası oluştur
        zip_path = Path(tempfile.gettempdir()) / f"output_files_{message.from_user.id}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in config.OUTPUT_DIR.glob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.name)
        
        await message.answer_document(
            FSInputFile(zip_path),
            caption="📁 Output dosyaları"
        )
        
        # Geçici zip dosyasını sil
        zip_path.unlink()
        
    except Exception as e:
        logger.error(f"Output indirme hatası: {e}")
        await message.answer("❌ Dosyalar indirilemedi.")

async def download_log_files(message: Message):
    """Log dosyalarını zip olarak indir"""
    try:
        if not config.LOGS_DIR.exists() or not any(config.LOGS_DIR.iterdir()):
            await message.answer("❌ Log klasörü boş veya mevcut değil.")
            return
        
        # Zip dosyası oluştur
        zip_path = Path(tempfile.gettempdir()) / f"log_files_{message.from_user.id}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in config.LOGS_DIR.glob('*'):
                if file_path.is_file():
                    zipf.write(file_path, file_path.name)
        
        await message.answer_document(
            FSInputFile(zip_path),
            caption="📝 Log dosyaları"
        )
        
        # Geçici zip dosyasını sil
        zip_path.unlink()
        
    except Exception as e:
        logger.error(f"Log indirme hatası: {e}")
        await message.answer("❌ Log dosyaları indirilemedi.")

async def clear_all(message: Message):
    """Output, Input ve temp temizliği"""
    try:
        cleared_files = 0
        cleared_size = 0
        
        # Input dizini
        if config.INPUT_DIR.exists():
            for file_path in config.INPUT_DIR.glob('*'):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleared_files += 1
                    cleared_size += file_size
        
        # Output dizini
        if config.OUTPUT_DIR.exists():
            for file_path in config.OUTPUT_DIR.glob('*'):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleared_files += 1
                    cleared_size += file_size
        
        # Temp dizini (varsa)
        temp_dir = Path(tempfile.gettempdir())
        for pattern in ['*.xlsx', '*.xls', '*.tmp']:
            for file_path in temp_dir.glob(pattern):
                if file_path.is_file():
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()
                        cleared_files += 1
                        cleared_size += file_size
                    except:
                        pass
        
        cleared_size_mb = cleared_size / (1024 * 1024)
        
        await message.answer(
            f"🧹 Temizlik tamamlandı!\n\n"
            f"• Silinen dosya: {cleared_files}\n"
            f"• Kazanılan alan: {cleared_size_mb:.2f} MB\n\n"
            f"Temizlenen klasörler:\n"
            f"• {config.INPUT_DIR.name}\n"
            f"• {config.OUTPUT_DIR.name}\n"
            f"• Geçici dosyalar"
        )
        
    except Exception as e:
        logger.error(f"Temizlik hatası: {e}")
        await message.answer("❌ Temizlik işlemi başarısız oldu.")

async def clear_logs(message: Message):
    """Log dosyalarını temizle"""
    try:
        cleared_files = 0
        cleared_size = 0
        
        if config.LOGS_DIR.exists():
            for file_path in config.LOGS_DIR.glob('*'):
                if file_path.is_file():
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleared_files += 1
                    cleared_size += file_size
        
        cleared_size_mb = cleared_size / (1024 * 1024)
        
        await message.answer(
            f"📝 Log temizliği tamamlandı!\n\n"
            f"• Silinen dosya: {cleared_files}\n"
            f"• Kazanılan alan: {cleared_size_mb:.2f} MB"
        )
        
    except Exception as e:
        logger.error(f"Log temizleme hatası: {e}")
        await message.answer("❌ Log temizleme işlemi başarısız oldu.")