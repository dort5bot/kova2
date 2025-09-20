# Excel İşleme Görevi (jobs/process_excel.py)
import asyncio
from pathlib import Path
from typing import Dict, Any

from utils.excel_cleaner import clean_excel_headers
from utils.excel_splitter import split_excel_by_groups
from utils.mailer import send_email_with_attachment
from utils.group_manager import group_manager
from utils.logger import logger

async def process_excel_task(input_path: Path, user_id: int) -> Dict[str, Any]:
    """Excel işleme görevini yürütür"""
    try:
        # 1. Excel dosyasını temizle ve düzenle
        cleaning_result = clean_excel_headers(str(input_path))
        if not cleaning_result["success"]:
            return {"success": False, "error": cleaning_result["error"]}
        
        # 2. Dosyayı gruplara ayır
        splitting_result = split_excel_by_groups(
            cleaning_result["temp_path"],
            cleaning_result["headers"]
        )
        
        if not splitting_result["success"]:
            return {"success": False, "error": splitting_result["error"]}
        
        # 3. E-postaları gönder (async olarak)
        email_tasks = []
        output_files = splitting_result["output_files"]
        
        for group_id, file_info in output_files.items():
            group_info = group_manager.get_group_info(group_id)
            recipients = group_info.get("email_recipients", [])
            
            if recipients and file_info["row_count"] > 0:  # Boş dosya gönderme
                subject = f"{group_info.get('group_name', group_id)} Raporu"
                body = f"Ekte {file_info['row_count']} satırlık rapor bulunmaktadır."
                
                task = send_email_with_attachment(
                    recipients, subject, body, file_info["path"]
                )
                email_tasks.append(task)
                
                # Mail gönderim işaretini ekle
                file_info["email_sent"] = True
        
        # Tüm mail görevlerini paralel çalıştır
        if email_tasks:
            email_results = await asyncio.gather(*email_tasks, return_exceptions=True)
            
            # Hataları logla
            for i, result in enumerate(email_results):
                if isinstance(result, Exception):
                    logger.error(f"Mail gönderim hatası: {result}")
        
        # Geçici dosyayı temizle
        try:
            Path(cleaning_result["temp_path"]).unlink()
        except:
            pass
        
        return {
            "success": True,
            "output_files": output_files,
            "total_rows": splitting_result["total_rows"],
            "matched_rows": splitting_result["matched_rows"]
        }
        
    except Exception as e:
        logger.error(f"İşlem görevi hatası: {e}")
        return {"success": False, "error": str(e)}
