"""
Admin Handler (handlers/admin_handler.py)
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, BufferedInputFile
from aiogram.filters import Command, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
import aiofiles
import aiofiles.os
import json
import shutil
from typing import Dict, List, Any

from config import config
from utils.logger import logger
from utils.file_utils import get_file_stats, get_directory_size, get_recent_processed_files
from utils.group_manager import group_manager
from utils.mailer import send_email_with_attachment

router = Router()

class AdminStates(StatesGroup):
    waiting_for_group_file = State()
    waiting_for_broadcast = State()

def is_admin(user_id: int) -> bool:
    """Kullanıcının admin olup olmadığını kontrol eder"""
    return user_id in config.ADMIN_CHAT_IDS

@router.message(Command("admin"))
async def cmd_admin(message: Message):
    """Admin panelini gösterir"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Bu komutu kullanma yetkiniz yok.")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 İstatistikler", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📝 Logları Görüntüle", callback_data="admin_logs")],
            [InlineKeyboardButton(text="👥 Grupları Yönet", callback_data="admin_groups")],
            [InlineKeyboardButton(text="🔄 Grup Dosyası Yükle", callback_data="admin_upload_groups")],
            [InlineKeyboardButton(text="📧 Toplu Mail Gönder", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🧹 Temizlik Yap", callback_data="admin_clean")],
            [InlineKeyboardButton(text="🚀 Sistem Durumu", callback_data="admin_system")]
        ]
    )
    
    await message.answer(
        "👑 **Admin Paneli**\n\n"
        "Aşağıdaki seçeneklerden birini seçin:",
        reply_markup=keyboard
    )

@router.callback_query(F.data.startswith("admin_"))
async def handle_admin_callback(callback: CallbackQuery, state: FSMContext):
    """Admin callback'lerini işler"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Yetkiniz yok.")
        return
    
    action = callback.data
    
    if action == "admin_stats":
        await show_admin_stats(callback.message)
    elif action == "admin_logs":
        await show_admin_logs(callback.message)
    elif action == "admin_groups":
        await show_group_management(callback.message)
    elif action == "admin_upload_groups":
        await callback.message.answer("📁 Lütfen yeni grup JSON dosyasını gönderin.")
        await callback.message.delete()
        await state.set_state(AdminStates.waiting_for_group_file)
    elif action == "admin_broadcast":
        await callback.message.answer("📢 Lütfen göndermek istediğiniz mesajı yazın:")
        await callback.message.delete()
        await state.set_state(AdminStates.waiting_for_broadcast)
    elif action == "admin_clean":
        await clean_system(callback.message)
    elif action == "admin_system":
        await show_system_status(callback.message)
    
    await callback.answer()

async def show_admin_stats(message: Message):
    """Detaylı admin istatistiklerini gösterir"""
    try:
        stats = await get_file_stats(detailed=True)
        
        # Disk kullanımı
        input_size = await get_directory_size(config.INPUT_DIR)
        output_size = await get_directory_size(config.OUTPUT_DIR)
        logs_size = await get_directory_size(config.LOGS_DIR)
        
        stats_message = (
            "📈 **Admin İstatistikleri**\n\n"
            f"📊 Toplam işlenen dosya: {stats['total_processed']}\n"
            f"✅ Başarılı işlem: {stats['successful_processed']}\n"
            f"❌ Başarısız işlem: {stats['failed_processed']}\n"
            f"📧 Gönderilen mail: {stats['emails_sent']}\n\n"
            f"📅 Zaman Bazlı:\n"
            f"  Son 24 saat: {stats['last_24h_processed']} dosya\n"
            f"  Son 7 gün: {stats['last_7d_processed']} dosya\n\n"
            f"💾 Disk Kullanımı:\n"
            f"  Input: {input_size}\n"
            f"  Output: {output_size}\n"
            f"  Logs: {logs_size}\n\n"
            f"📈 Toplam satır: {stats['total_rows']}"
        )
        
        await message.answer(stats_message)
        
    except Exception as e:
        logger.error(f"Admin stats hatası: {e}")
        await message.answer("❌ İstatistikler alınamadı.")

async def show_admin_logs(message: Message):
    """Admin loglarını gösterir"""
    try:
        log_path = config.LOGS_DIR / "bot.log"
        error_path = config.LOGS_DIR / "errors.log"
        
        if not log_path.exists():
            await message.answer("📝 Log dosyası bulunamadı.")
            return
        
        # Son 50 satırı oku
        async with aiofiles.open(log_path, 'r', encoding='utf-8') as f:
            lines = await f.readlines()
            last_lines = lines[-50:] if len(lines) > 50 else lines
        
        if not last_lines:
            await message.answer("📝 Log dosyası boş.")
            return
        
        log_content = "".join(last_lines)
        
        # Hata loglarını da kontrol et
        error_count = 0
        if error_path.exists():
            async with aiofiles.open(error_path, 'r', encoding='utf-8') as f:
                error_lines = await f.readlines()
                error_count = len(error_lines)
        
        # Telegram mesaj sınırı
        if len(log_content) > 4000:
            log_content = log_content[-4000:]
        
        response = (
            f"📝 **Son 50 Log Satırı**\n"
            f"❌ Hata sayısı: {error_count}\n\n"
            f"```\n{log_content}\n```"
        )
        
        await message.answer(response, parse_mode="Markdown")
        
    except Exception as e:
        logger.error(f"Admin logs hatası: {e}")
        await message.answer("❌ Loglar alınamadı.")

async def show_group_management(message: Message):
    """Grup yönetim panelini gösterir"""
    try:
        groups = group_manager.groups.get("groups", [])
        
        if not groups:
            await message.answer("❌ Hiç grup tanımlanmamış.")
            return
        
        groups_info = []
        for i, group in enumerate(groups, 1):
            group_id = group.get("group_id", "Bilinmiyor")
            group_name = group.get("group_name", "İsimsiz")
            city_count = len(group.get("cities", []))
            email_count = len(group.get("email_recipients", []))
            
            groups_info.append(
                f"{i}. {group_name} ({group_id})\n"
                f"   🏙️ {city_count} şehir, 📧 {email_count} alıcı"
            )
        
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Grupları Yenile", callback_data="admin_refresh_groups")],
                [InlineKeyboardButton(text="📋 Grup Detayları", callback_data="admin_group_details")],
                [InlineKeyboardButton(text="◀️ Geri", callback_data="admin_back")]
            ]
        )
        
        response = (
            "👥 **Grup Yönetimi**\n\n"
            f"Toplam {len(groups)} grup tanımlı:\n\n"
            + "\n".join(groups_info)
        )
        
        await message.answer(response, reply_markup=keyboard)
        
    except Exception as e:
        logger.error(f"Grup yönetimi hatası: {e}")
        await message.answer("❌ Grup bilgileri alınamadı.")

# Admin handler'a grupları yenileme fonksiyonu ekleyin:
@router.callback_query(F.data == "admin_refresh_groups")
async def refresh_groups(callback: CallbackQuery):
    """Grupları yeniden yükler"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Yetkiniz yok.")
        return
    
    try:
        # Grup manager'ı yeniden başlat
        group_manager.refresh_groups()
        
        await callback.message.edit_text(
            "✅ Gruplar başarıyla yenilendi!\n"
            f"Toplam {len(group_manager.groups.get('groups', []))} grup yüklendi.\n"
            f"Şehir eşleştirme tablosu güncellendi."
        )
        
    except Exception as e:
        logger.error(f"Grup yenileme hatası: {e}")
        await callback.message.edit_text("❌ Gruplar yenilenirken hata oluştu.")
    
    await callback.answer()

@router.message(AdminStates.waiting_for_group_file, F.document)
async def handle_group_file_upload(message: Message, state: FSMContext):
    """Grup JSON dosyasını işler"""
    try:
        file_id = message.document.file_id
        file_name = message.document.file_name
        
        if not file_name.endswith('.json'):
            await message.answer("❌ Lütfen JSON dosyası gönderin.")
            await state.clear()
            return
        
        # Dosyayı indir
        bot = message.bot
        file = await bot.get_file(file_id)
        file_path = config.GROUPS_DIR / "groups_new.json"
        
        await bot.download_file(file.file_path, file_path)
        
        # Dosyayı doğrula
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                groups_data = json.load(f)
            
            # Basit doğrulama
            if "groups" not in groups_data or not isinstance(groups_data["groups"], list):
                raise ValueError("Geçersiz grup dosyası formatı")
            
            # Yedek al
            backup_path = config.GROUPS_DIR / f"groups_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            if (config.GROUPS_DIR / "groups.json").exists():
                shutil.copy2(config.GROUPS_DIR / "groups.json", backup_path)
            
            # Yeni dosyayı aktif et
            shutil.move(file_path, config.GROUPS_DIR / "groups.json")
            
            # Grupları yenile
            group_manager.groups = group_manager.load_groups()
            group_manager.city_to_group = group_manager.build_city_mapping()
            
            await message.answer(
                "✅ Grup dosyası başarıyla güncellendi!\n"
                f"Toplam {len(group_manager.groups.get('groups', []))} grup yüklendi.\n"
                f"Yedek: {backup_path.name}"
            )
            
        except Exception as e:
            await message.answer(f"❌ Geçersiz grup dosyası: {str(e)}")
            file_path.unlink()  # Geçersiz dosyayı sil
        
    except Exception as e:
        logger.error(f"Grup dosyası yükleme hatası: {e}")
        await message.answer("❌ Dosya işlenirken hata oluştu.")
    finally:
        await state.clear()

@router.message(AdminStates.waiting_for_broadcast)
async def handle_broadcast_message(message: Message, state: FSMContext):
    """Toplu mesaj gönderimini işler"""
    try:
        # Tüm adminlere mesajı gönder
        sent_count = 0
        failed_count = 0
        
        for admin_id in config.ADMIN_CHAT_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"📢 **Toplu Bildirim**\n\n{message.text}"
                )
                sent_count += 1
            except Exception as e:
                logger.error(f"Toplu mesaj gönderilemedi {admin_id}: {e}")
                failed_count += 1
        
        await message.answer(
            f"✅ Toplu mesaj gönderildi!\n"
            f"Başarılı: {sent_count}\n"
            f"Başarısız: {failed_count}"
        )
        
    except Exception as e:
        logger.error(f"Toplu mesaj hatası: {e}")
        await message.answer("❌ Toplu mesaj gönderilemedi.")
    finally:
        await state.clear()

async def clean_system(message: Message):
    """Sistem temizliği yapar"""
    try:
        cleaned_files = 0
        cleaned_size = 0
        now = datetime.now()
        
        # Input dizini (24 saatten eski)
        for file_path in config.INPUT_DIR.glob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if now - file_time > timedelta(hours=24):
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_files += 1
                    cleaned_size += file_size
        
        # Output dizini (7 günden eski)
        for file_path in config.OUTPUT_DIR.glob("*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if now - file_time > timedelta(days=7):
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_files += 1
                    cleaned_size += file_size
        
        # Eski log backup'ları (30 günden eski)
        for file_path in config.LOGS_DIR.glob("*.log.*"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if now - file_time > timedelta(days=30):
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_files += 1
                    cleaned_size += file_size
        
        # Eski grup backup'ları (30 günden eski)
        for file_path in config.GROUPS_DIR.glob("groups_backup_*.json"):
            if file_path.is_file():
                file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                if now - file_time > timedelta(days=30):
                    file_size = file_path.stat().st_size
                    file_path.unlink()
                    cleaned_files += 1
                    cleaned_size += file_size
        
        cleaned_size_mb = cleaned_size / (1024 * 1024)
        
        await message.answer(
            f"🧹 **Sistem Temizliği Tamamlandı**\n\n"
            f"Silinen dosya: {cleaned_files}\n"
            f"Kazanılan alan: {cleaned_size_mb:.2f} MB\n\n"
            f"• 24 saatten eski input dosyaları\n"
            f"• 7 günden eski output dosyaları\n"
            f"• 30 günden eski yedekler"
        )
        
    except Exception as e:
        logger.error(f"Sistem temizliği hatası: {e}")
        await message.answer("❌ Temizlik işlemi başarısız oldu.")

async def show_system_status(message: Message):
    """Sistem durumunu gösterir"""
    try:
        import psutil
        import platform
        from datetime import datetime
        
        # Sistem bilgileri
        system_info = {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "processor": platform.processor() or "Bilinmiyor",
            "python_version": platform.python_version()
        }
        
        # Bellek bilgileri
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Process bilgileri
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024 / 1024  # MB
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # Çalışma süresi
        uptime = datetime.now() - datetime.fromtimestamp(process.create_time())
        uptime_str = str(uptime).split('.')[0]  # Mikrosaniyeleri kaldır
        
        status_message = (
            "🚀 **Sistem Durumu**\n\n"
            f"🖥️ **Sistem:** {system_info['platform']} {system_info['platform_version']}\n"
            f"🐍 **Python:** {system_info['python_version']}\n"
            f"⚡ **İşlemci:** {system_info['processor'][:40]}...\n\n"
            f"📊 **Kaynak Kullanımı:**\n"
            f"  CPU: {cpu_percent}%\n"
            f"  Bellek: {memory_usage:.1f} MB ({memory.percent}% sistem)\n"
            f"  Disk: {disk.percent}% dolu\n\n"
            f"⏰ **Çalışma Süresi:** {uptime_str}\n"
            f"👑 **Admin Sayısı:** {len(config.ADMIN_CHAT_IDS)}"
        )
        
        await message.answer(status_message)
        
    except Exception as e:
        logger.error(f"Sistem durumu hatası: {e}")
        await message.answer("❌ Sistem durumu alınamadı.")

@router.message(Command("send_test_email"))
async def cmd_send_test_email(message: Message, command: CommandObject):
    """Test e-postası gönderir"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Bu komutu kullanma yetkiniz yok.")
        return
    
    try:
        email = command.args or config.SMTP_USERNAME
        if not email:
            await message.answer("❌ E-posta adresi belirtilmeli.")
            return
        
        # Test dosyası oluştur
        from openpyxl import Workbook
        test_wb = Workbook()
        test_ws = test_wb.active
        test_ws.title = "Test Verileri"
        test_ws['A1'] = "Test"
        test_ws['A2'] = "Başarılı!"
        
        test_file = config.OUTPUT_DIR / "test_email.xlsx"
        test_wb.save(test_file)
        test_wb.close()
        
        # E-posta gönder
        success = await send_email_with_attachment(
            [email],
            "📧 Test E-postası - Excel Bot",
            "Bu bir test e-postasıdır. Bot e-posta gönderme işlevi çalışıyor.",
            test_file
        )
        
        # Test dosyasını sil
        test_file.unlink()
        
        if success:
            await message.answer(f"✅ Test e-postası gönderildi: {email}")
        else:
            await message.answer(f"❌ Test e-postası gönderilemedi: {email}")
            
    except Exception as e:
        logger.error(f"Test e-postası hatası: {e}")
        await message.answer(f"❌ Test e-postası hatası: {str(e)}")

@router.message(Command("get_logfile"))
async def cmd_get_logfile(message: Message):
    """Log dosyasını gönderir"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ Bu komutu kullanma yetkiniz yok.")
        return
    
    try:
        log_path = config.LOGS_DIR / "bot.log"
        
        if not log_path.exists():
            await message.answer("❌ Log dosyası bulunamadı.")
            return
        
        # Dosya boyutunu kontrol et
        file_size = log_path.stat().st_size
        if file_size > 50 * 1024 * 1024:  # 50MB'den büyükse
            await message.answer("❌ Log dosyası çok büyük (50MB+).")
            return
        
        # Dosyayı gönder
        await message.bot.send_document(
            chat_id=message.chat.id,
            document=BufferedInputFile(
                log_path.read_bytes(),
                filename=f"bot_log_{datetime.now().strftime('%Y%m%d_%H%M')}.log"
            ),
            caption="📝 Bot log dosyası"
        )
        
    except Exception as e:
        logger.error(f"Log dosyası gönderme hatası: {e}")
        await message.answer("❌ Log dosyası gönderilemedi.")

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Admin paneline geri döner"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ Yetkiniz yok.")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 İstatistikler", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📝 Logları Görüntüle", callback_data="admin_logs")],
            [InlineKeyboardButton(text="👥 Grupları Yönet", callback_data="admin_groups")],
            [InlineKeyboardButton(text="🔄 Grup Dosyası Yükle", callback_data="admin_upload_groups")],
            [InlineKeyboardButton(text="📧 Toplu Mail Gönder", callback_data="admin_broadcast")],
            [InlineKeyboardButton(text="🧹 Temizlik Yap", callback_data="admin_clean")],
            [InlineKeyboardButton(text="🚀 Sistem Durumu", callback_data="admin_system")]
        ]
    )
    
    await callback.message.edit_text(
        "👑 **Admin Paneli**\n\n"
        "Aşağıdaki seçeneklerden birini seçin:",
        reply_markup=keyboard
    )
    
    await callback.answer()

# Hata durumları için handler'lar
@router.message(AdminStates.waiting_for_group_file)
async def handle_wrong_group_file(message: Message):
    """Yanlış grup dosyası tipi"""
    await message.answer("❌ Lütfen bir JSON dosyası gönderin.")

@router.message(AdminStates.waiting_for_broadcast)
async def handle_empty_broadcast(message: Message):
    """Boş broadcast mesajı"""
    await message.answer("❌ Lütfen geçerli bir mesaj yazın.")