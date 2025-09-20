# handlers/status_handler.py
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from datetime import datetime, timedelta
import aiofiles
from config import config
from utils.logger import logger
from utils.file_utils import get_recent_processed_files, get_file_stats

router = Router()

@router.message(Command("status"))
async def cmd_status(message: Message):
    try:
        stats = await get_file_stats()

        log_size = "Bilinmiyor"
        try:
            log_path = config.LOGS_DIR / "bot.log"
            if log_path.exists():
                log_size = f"{(log_path.stat().st_size / 1024):.1f} KB"
        except:
            pass

        status_message = (
            "📊 <b>Sistem Durumu</b>\n\n"
            f"✅ Bot çalışıyor\n"
            f"📁 İşlenen dosya: {stats['total_processed']}\n"
            f"📊 Satır: {stats['total_rows']}\n"
            f"📝 Log boyutu: {log_size}\n"
            f"💾 Bellek kullanımı: {stats['memory_usage']}\n"
            f"🔄 Son işlem: {stats['last_processed']}"
        )

        await message.answer(status_message)
    except Exception as e:
        logger.error(f"Status komutu hatası: {e}")
        await message.answer("❌ Durum bilgisi alınamadı.")

@router.message(Command("files"))
async def cmd_files(message: Message):
    try:
        files = await get_recent_processed_files()
        if not files:
            await message.answer("📁 Hiç işlenen dosya yok.")
            return

        text = "📁 <b>Son Dosyalar:</b>\n\n"
        for i, f in enumerate(files, 1):
            text += f"{i}. {f['name']} ({f['size']} - {f['modified'].strftime('%d.%m.%Y %H:%M')})\n"

        await message.answer(text)
    except Exception as e:
        logger.error(f"Files komutu hatası: {e}")
        await message.answer("❌ Dosya listesi alınamadı.")

@router.message(Command("logs"))
async def cmd_logs(message: Message):
    try:
        log_path = config.LOGS_DIR / "bot.log"
        if not log_path.exists():
            await message.answer("📝 Log dosyası bulunamadı.")
            return

        async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
            lines = await f.readlines()
            last_lines = lines[-20:] if len(lines) > 20 else lines

        log_content = "".join(last_lines)
        if len(log_content) > 4000:
            log_content = log_content[-4000:]

        await message.answer(f"<b>Son Loglar:</b>\n<pre>{log_content}</pre>", parse_mode="HTML")
    except Exception as e:
        logger.error(f"Logs komutu hatası: {e}")
        await message.answer("❌ Loglar alınamadı.")
