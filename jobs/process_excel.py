# jobs/process_excel.py - OPTIMIZE EDİLMİŞ VERSİYON
"""
Excel İşleme Görevi - Optimize Edilmiş
Tek bir ana fonksiyon ile tüm modları destekler
"""

import asyncio
import zipfile
import tempfile
from pathlib import Path
from typing import Dict, Any, List
from openpyxl import load_workbook

from utils.excel_cleaner import clean_excel_headers
from utils.excel_splitter import split_excel_by_groups
from utils.mailer import send_email_with_attachment
from utils.group_manager import group_manager
from utils.logger import logger
from config import config


class ProcessMode:
    """İşlem modları için sabitler"""
    NORMAL = "normal"  # Gruplara ayırıp her grubun mail listesine gönder
    PERSONAL = "personal"  # Tek dosya olarak kişisel maile gönder
    ZIP = "zip"  # Gruplara ayırıp ZIP yaparak kişisel maile gönder


async def process_excel_task(input_path: Path, user_id: int, mode: str = ProcessMode.ZIP) -> Dict[str, Any]:
    """
    Excel işleme görevini yürütür - Tüm modları destekler
    
    Args:
        input_path: Girdi Excel dosyası yolu
        user_id: Kullanıcı ID'si
        mode: İşlem modu (normal, personal, zip)
    
    Returns:
        İşlem sonucu sözlüğü
    """
    cleaning_result = None
    temp_output_path = None
    
    try:
        logger.info(f"Excel işleme başlatıldı: {input_path.name}, Kullanıcı: {user_id}, Mod: {mode}")

        # 1. Excel dosyasını temizle ve düzenle
        cleaning_result = clean_excel_headers(str(input_path))
        if not cleaning_result["success"]:
            error_msg = f"Excel temizleme hatası: {cleaning_result.get('error', 'Bilinmeyen hata')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        logger.info(f"Excel temizlendi: {cleaning_result['row_count']} satır")

        # MODA GÖRE İŞLEM YAP
        if mode == ProcessMode.PERSONAL:
            result = await _process_personal_mode(cleaning_result, input_path.name)
        elif mode == ProcessMode.NORMAL:
            result = await _process_normal_mode(cleaning_result)
        else:  # ZIP mod (varsayılan)
            result = await _process_zip_mode(cleaning_result, input_path.name)
        
        result["user_id"] = user_id
        result["mode"] = mode
        return result
        
    except Exception as e:
        logger.error(f"İşlem görevi hatası: {e}", exc_info=True)
        return {"success": False, "error": str(e)}
    finally:
        # Geçici dosyaları temizle
        await _cleanup_temp_files(cleaning_result, temp_output_path)


async def _process_personal_mode(cleaning_result: Dict, original_filename: str) -> Dict[str, Any]:
    """Kişisel mail modu işlemi"""
    temp_output_path = None
    try:
        # Temizlenmiş dosyayı yükle ve formatla
        wb = load_workbook(cleaning_result["temp_path"])
        ws = wb.active
        
        # Sütun genişliklerini ayarla
        from openpyxl.utils import get_column_letter
        for column_cells in ws.columns:
            length = max(len(str(cell.value)) if cell.value else 0 for cell in column_cells)
            column_letter = get_column_letter(column_cells[0].column)
            ws.column_dimensions[column_letter].width = min(25, max(length + 2, 10))
        
        # Geçici çıktı dosyası oluştur
        temp_output = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
        temp_output_path = temp_output.name
        wb.save(temp_output_path)
        wb.close()
        
        # Kişisel maile gönder
        email_success = False
        if config.PERSONAL_EMAIL:
            subject = f"📊 Excel Raporu - {original_filename}"
            body = (
                f"Merhaba,\n\n"
                f"{cleaning_result['row_count']} satırlık Excel raporu ekte gönderilmiştir.\n\n"
                f"İyi çalışmalar,\nExcel Bot"
            )
            
            email_success = await send_email_with_attachment(
                [config.PERSONAL_EMAIL], subject, body, Path(temp_output_path)
            )
        
        return {
            "success": email_success,
            "total_rows": cleaning_result["row_count"],
            "email_sent_to": config.PERSONAL_EMAIL if email_success else None
        }
        
    except Exception as e:
        logger.error(f"Kişisel mail işleme hatası: {e}")
        return {"success": False, "error": str(e)}


async def _process_normal_mode(cleaning_result: Dict) -> Dict[str, Any]:
    """Normal mod işlemi (gruplara ayırıp her gruba mail)"""
    try:
        # Dosyayı gruplara ayır
        splitting_result = split_excel_by_groups(
            cleaning_result["temp_path"],
            cleaning_result["headers"]
        )
        
        if not splitting_result["success"]:
            error_msg = f"Excel ayırma hatası: {splitting_result.get('error', 'Bilinmeyen hata')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        logger.info(f"Excel gruplara ayrıldı: {splitting_result['total_rows']} satır, {len(splitting_result['output_files'])} grup")

        # E-postaları gönder (async olarak)
        email_tasks = []
        output_files = splitting_result["output_files"]
        email_results = []
        
        for group_id, file_info in output_files.items():
            group_info = group_manager.get_group_info(group_id)
            recipients = group_info.get("email_recipients", [])
            
            if recipients and file_info["row_count"] > 0:
                subject = f"{group_info.get('group_name', group_id)} Raporu - {file_info['filename']}"
                body = (
                    f"Merhaba,\n\n"
                    f"{group_info.get('group_name', group_id)} grubu için {file_info['row_count']} satırlık rapor ekte gönderilmiştir.\n\n"
                    f"İyi çalışmalar,\nExcel Bot"
                )
                
                for recipient in recipients:
                    if recipient.strip():
                        task = send_email_with_attachment(
                            [recipient.strip()], subject, body, file_info["path"]
                        )
                        email_tasks.append((task, group_id, recipient, file_info["path"].name))
        
        # Tüm mail görevlerini paralel çalıştır
        if email_tasks:
            logger.info(f"{len(email_tasks)} mail görevi başlatılıyor...")
            tasks = [task[0] for task in email_tasks]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sonuçları işle
            for i, result in enumerate(results):
                task_info = email_tasks[i]
                group_id, recipient, filename = task_info[1], task_info[2], task_info[3]
                
                if isinstance(result, Exception):
                    logger.error(f"Mail gönderim hatası - Grup: {group_id}, Alıcı: {recipient}, Dosya: {filename}, Hata: {result}")
                    email_results.append({
                        "success": False,
                        "group_id": group_id,
                        "recipient": recipient,
                        "error": str(result)
                    })
                else:
                    logger.info(f"Mail gönderildi - Grup: {group_id}, Alıcı: {recipient}, Dosya: {filename}")
                    email_results.append({
                        "success": True,
                        "group_id": group_id,
                        "recipient": recipient
                    })
        
        successful_emails = sum(1 for res in email_results if res["success"])
        logger.info(f"Mail gönderim sonucu: {successful_emails} başarılı, {len(email_results) - successful_emails} başarısız")
        
        return {
            "success": True,
            "output_files": output_files,
            "total_rows": splitting_result["total_rows"],
            "matched_rows": splitting_result["matched_rows"],
            "email_results": email_results,
            "email_sent": successful_emails > 0
        }
        
    except Exception as e:
        logger.error(f"Normal mod işleme hatası: {e}")
        return {"success": False, "error": str(e)}


async def _process_zip_mode(cleaning_result: Dict, original_filename: str) -> Dict[str, Any]:
    """ZIP modu işlemi"""
    try:
        # Dosyayı gruplara ayır
        splitting_result = split_excel_by_groups(
            cleaning_result["temp_path"],
            cleaning_result["headers"]
        )
        
        if not splitting_result["success"]:
            error_msg = f"Excel ayırma hatası: {splitting_result.get('error', 'Bilinmeyen hata')}"
            logger.error(error_msg)
            return {"success": False, "error": error_msg}
        
        logger.info(f"Excel gruplara ayrıldı: {splitting_result['total_rows']} satır, {len(splitting_result['output_files'])} grup")

        # Tüm dosyaları ZIP yap ve PERSONAL_EMAIL'e gönder
        zip_success = False
        output_files = splitting_result["output_files"]
        
        if output_files and config.PERSONAL_EMAIL:
            zip_success = await _send_zip_to_personal_email(output_files, original_filename)
        
        return {
            "success": zip_success,
            "output_files": output_files,
            "total_rows": splitting_result["total_rows"],
            "matched_rows": splitting_result["matched_rows"],
            "personal_email": config.PERSONAL_EMAIL,
            "zip_sent": zip_success
        }
        
    except Exception as e:
        logger.error(f"ZIP mod işleme hatası: {e}")
        return {"success": False, "error": str(e)}


async def _send_zip_to_personal_email(output_files: Dict[str, Any], original_filename: str) -> bool:
    """Tüm çıktı dosyalarını ZIP yapıp PERSONAL_EMAIL'e gönderir"""
    if not config.PERSONAL_EMAIL:
        logger.error("PERSONAL_EMAIL tanımlı değil")
        return False
    
    try:
        # ZIP dosyası oluştur
        zip_path = Path(tempfile.gettempdir()) / f"excel_output_{original_filename.split('.')[0]}.zip"
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_info in output_files.values():
                zipf.write(file_info["path"], file_info["filename"])
        
        # Mail gönder
        subject = f"📊 Excel Grup Raporları - {original_filename}"
        body = (
            f"Excel işleme sonucu oluşturulan {len(output_files)} dosya ektedir.\n\n"
            f"Toplam satır: {sum(f['row_count'] for f in output_files.values())}\n"
            f"Oluşan gruplar: {', '.join(f['filename'] for f in output_files.values())}\n\n"
            f"İyi çalışmalar,\nExcel Bot"
        )
        
        success = await send_email_with_attachment(
            [config.PERSONAL_EMAIL],
            subject,
            body,
            zip_path
        )
        
        # ZIP dosyasını sil
        zip_path.unlink(missing_ok=True)
        
        if success:
            logger.info(f"ZIP dosyası başarıyla gönderildi: {config.PERSONAL_EMAIL}")
        else:
            logger.error(f"ZIP dosyası gönderilemedi: {config.PERSONAL_EMAIL}")
        
        return success
        
    except Exception as e:
        logger.error(f"ZIP gönderme hatası: {e}")
        return False


async def _cleanup_temp_files(cleaning_result: Dict, temp_output_path: str = None):
    """Geçici dosyaları temizler"""
    try:
        if cleaning_result and "temp_path" in cleaning_result:
            temp_path = Path(cleaning_result["temp_path"])
            if temp_path.exists():
                temp_path.unlink()
                logger.info(f"Geçici dosya silindi: {temp_path.name}")
        
        if temp_output_path and Path(temp_output_path).exists():
            Path(temp_output_path).unlink()
            logger.info(f"Geçici output dosyası silindi: {temp_output_path}")
    except Exception as e:
        logger.warning(f"Geçici dosya silinemedi: {e}")


# Geriye uyumluluk için eski fonksiyonlar
async def process_excel_task_with_zip(input_path: Path, user_id: int) -> Dict[str, Any]:
    """ZIP modu için geriye uyumlu fonksiyon"""
    return await process_excel_task(input_path, user_id, ProcessMode.ZIP)


async def process_excel_task_for_personal_email(input_path: Path, user_id: int) -> Dict[str, Any]:
    """Kişisel mail modu için geriye uyumlu fonksiyon"""
    return await process_excel_task(input_path, user_id, ProcessMode.PERSONAL)