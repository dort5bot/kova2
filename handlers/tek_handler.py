# handlers/tek_handler.py
"""
/process komutu gruplara ayırıp her grubun kendi email listesine gönderim yapar
/bana komutu tüm veriyi tek dosya olarak kişisel maile gönderir

/tek komutu
/process ve /bana komutlarından farklı olarak 
hem gruplama yapar hem de gönderimi kişiselleştirir.

/tek komutu gruplara ayırma işlemini yapar + sadece kişisel maile yapacak

/tek komutu gruplara ayırma işlemi yapar
- groups.json'daki grup bilgilerini kullanır
- Oluşan tüm dosyaları (antalya_sube.xlsx, izmir_sube.xlsx vb.)
- Sadece PERSONAL_EMAIL'e gönderir
- Grupların kendi email listelerine göndermez
- Zip dosyası olarak tek mailde gönderir
- Detaylı rapor sunar

main.py dosyasına import ekleyin:
# main.py'ye ekle
from handlers.tek_handler import router as tek_router

# Router'ları yükleme kısmına ekle
dp.include_router(tek_router)  # Diğer router'lardan sonra


handlers/reply_handler.py dosyasına TEK butonu ekle
# reply_handler.py'de keyboard'a ekle

# TEK butonu handler'ı ekle

"""
from typing import Dict, Any

from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from config import config
from utils.excel_cleaner import clean_excel_headers
from utils.excel_splitter import split_excel_by_groups
from utils.validator import validate_excel_file
from utils.mailer import send_email_with_attachment
from utils.reporter import generate_processing_report
from utils.logger import logger

import tempfile
import asyncio
from pathlib import Path

router = Router()

class TekProcessingStates(StatesGroup):
    waiting_for_file = State()

@router.message(Command("tek"))
async def cmd_tek(message: Message, state: FSMContext):
    """Tek işlem komutu - gruplara ayırır ama sadece kişisel maile gönderir"""
    await state.set_state(TekProcessingStates.waiting_for_file)
    await message.answer(
        "📊 TEK İŞLEM MODU\n\n"
        "Lütfen Excel dosyasını gönderin.\n"
        "• Dosya gruplara ayrılacak\n"
        "• Tüm çıktılar sadece kişisel maile gönderilecek\n"
        f"• Alıcı: {config.PERSONAL_EMAIL}"
    )

@router.message(TekProcessingStates.waiting_for_file, F.document)
async def handle_tek_excel_upload(message: Message, state: FSMContext):
    """Tek işlem için Excel dosyasını işler"""
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
        validation_result = validate_excel_file(str(file_path))
        if not validation_result["valid"]:
            await message.answer(f"❌ {validation_result['message']}")
            await state.clear()
            file_path.unlink()
            return
        
        await message.answer("⏳ TEK işlem başlatıldı...")
        
        # TEK işlemini gerçekleştir
        task_result = await process_tek_task(file_path, message.from_user.id)
        
        if task_result["success"]:
            # Rapor oluştur
            report = generate_tek_report(task_result)
            await message.answer(report)
            
            # Dosyaları kullanıcıya da gönder (opsiyonel)
            for file_info in task_result["output_files"].values():
                try:
                    await message.answer_document(
                        BufferedInputFile(
                            file_info["path"].read_bytes(),
                            filename=file_info["filename"]
                        ),
                        caption=f"📁 {file_info['filename']}"
                    )
                except Exception as e:
                    logger.warning(f"Dosya gönderilemedi {file_info['filename']}: {e}")
        else:
            await message.answer(f"❌ İşlem sırasında hata oluştu: {task_result['error']}")
        
    except Exception as e:
        logger.error(f"TEK işleme hatası: {e}")
        await message.answer("❌ Dosya işlenirken bir hata oluştu.")
    finally:
        await state.clear()

@router.message(TekProcessingStates.waiting_for_file)
async def handle_tek_wrong_file_type(message: Message):
    await message.answer("❌ Lütfen bir Excel dosyası gönderin.")

async def process_tek_task(input_path: Path, user_id: int) -> Dict[str, Any]:
    """TEK işlemi için özel görev"""
    cleaning_result = None
    try:
        logger.info(f"TEK işlemi başlatıldı: {input_path.name}, Kullanıcı: {user_id}")

        # 1. Excel dosyasını temizle
        cleaning_result = clean_excel_headers(str(input_path))
        if not cleaning_result["success"]:
            return {"success": False, "error": cleaning_result.get("error", "Temizleme hatası")}
        
        # 2. Dosyayı gruplara ayır (normal işlem gibi)
        splitting_result = split_excel_by_groups(
            cleaning_result["temp_path"],
            cleaning_result["headers"]
        )
        
        if not splitting_result["success"]:
            return {"success": False, "error": splitting_result.get("error", "Ayırma hatası")}
        
        # 3. Tüm çıktı dosyalarını TEK maile gönder
        email_success = False
        output_files = splitting_result["output_files"]
        
        if output_files and config.PERSONAL_EMAIL:
            # Tüm dosyaları tek mailde gönder
            email_success = await send_multiple_files_email(output_files)
        
        return {
            "success": email_success,
            "output_files": output_files,
            "total_rows": splitting_result["total_rows"],
            "matched_rows": splitting_result["matched_rows"],
            "user_id": user_id,
            "personal_email": config.PERSONAL_EMAIL
        }
        
    except Exception as e:
        logger.error(f"TEK işlem hatası: {e}")
        return {"success": False, "error": str(e)}
    finally:
        # Geçici dosyaları temizle
        try:
            if cleaning_result and "temp_path" in cleaning_result:
                Path(cleaning_result["temp_path"]).unlink(missing_ok=True)
        except:
            pass

async def send_multiple_files_email(output_files: Dict[str, Any]) -> bool:
    """Birden fazla dosyayı tek mailde gönderir"""
    if not config.PERSONAL_EMAIL:
        logger.error("PERSONAL_EMAIL tanımlı değil")
        return False
    
    try:
        # Tüm dosyaları zip yap
        import zipfile
        import tempfile
        
        zip_path = Path(tempfile.gettempdir()) / "tek_islem_output.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in output_files.values():
                zipf.write(file_info["path"], file_info["filename"])
        
        # Mail gönder
        subject = "📊 TEK İŞLEM - Grup Raporları"
        body = (
            f"TEK işlem sonucu oluşturulan {len(output_files)} dosya ektedir.\n\n"
            f"Toplam satır: {sum(f['row_count'] for f in output_files.values())}\n"
            f"Oluşan gruplar: {', '.join(f['filename'] for f in output_files.values())}"
        )
        
        success = await send_email_with_attachment(
            [config.PERSONAL_EMAIL],
            subject,
            body,
            zip_path
        )
        
        # Zip dosyasını sil
        zip_path.unlink(missing_ok=True)
        
        return success
        
    except Exception as e:
        logger.error(f"Çoklu dosya mail gönderme hatası: {e}")
        return False

def generate_tek_report(result: Dict) -> str:
    """TEK işlem raporu oluşturur"""
    if not result.get("success", False):
        return f"❌ TEK işlem başarısız: {result.get('error', 'Bilinmeyen hata')}"
    
    output_files = result.get("output_files", {})
    total_rows = result.get("total_rows", 0)
    matched_rows = result.get("matched_rows", 0)
    
    report_lines = [
        "✅ **TEK İŞLEM RAPORU**",
        f"📧 Gönderilen mail: {result.get('personal_email', 'Bilinmiyor')}",
        f"📊 Toplam satır: {total_rows}",
        f"✅ Eşleşen satır: {matched_rows}",
        f"📁 Oluşturulan dosya: {len(output_files)}",
        "",
        "📂 **GRUPLAR:**"
    ]
    
    for group_id, file_info in output_files.items():
        report_lines.append(f"• {file_info['filename']} ({file_info['row_count']} satır)")
    
    report_lines.extend([
        "",
        "📨 **DURUM:** Tüm dosyalar kişisel maile gönderildi ✅"
    ])
    
    return "\n".join(report_lines)