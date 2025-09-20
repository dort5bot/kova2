#Yardımcı Dosya İşlemleri (utils/file_utils.py)
"""
Bu status handler modülü, botun durumunu izlemek, 
logları görüntülemek, istatistikleri toplamak ve 
sistem yönetimi yapmak için kapsamlı bir dizi komut sağlar.
 Tüm komutlar kullanıcı dostu çıktılar üretir ve 
hata durumlarında uygun geri bildirim sağlar.

"""
# utils/file_utils.py

import os
from datetime import datetime
from pathlib import Path
import psutil
from config import config

async def get_recent_processed_files(limit: int = 10):
    """
    Output klasöründen son işlenen dosyaları döndürür.
    """
    files = []
    output_dir = config.OUTPUT_DIR

    if not output_dir.exists():
        return []

    for file_path in sorted(output_dir.glob("*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True):
        stat = file_path.stat()
        files.append({
            "name": file_path.name,
            "size": f"{stat.st_size / 1024:.1f} KB",
            "modified": datetime.fromtimestamp(stat.st_mtime)
        })
        if len(files) >= limit:
            break

    return files

async def get_file_stats(detailed=False):
    """
    İşlenen dosya sayısı ve sistem kaynak kullanımı gibi bilgileri verir.
    """
    total_processed = len(list(config.OUTPUT_DIR.glob("*.xlsx")))
    total_rows = 0
    successful_processed = total_processed
    failed_processed = 0
    emails_sent = total_processed

    last_processed = "Yok"
    files = sorted(config.OUTPUT_DIR.glob("*.xlsx"), key=lambda x: x.stat().st_mtime, reverse=True)
    if files:
        last_processed = datetime.fromtimestamp(files[0].stat().st_mtime).strftime("%d.%m.%Y %H:%M")

    process = psutil.Process()
    memory_usage = f"{process.memory_info().rss / 1024 / 1024:.1f} MB"

    stats = {
        "total_processed": total_processed,
        "total_rows": total_rows,
        "successful_processed": successful_processed,
        "failed_processed": failed_processed,
        "emails_sent": emails_sent,
        "last_processed": last_processed,
        "memory_usage": memory_usage
    }

    if detailed:
        stats.update({
            "last_24h_processed": total_processed,
            "last_7d_processed": total_processed,
            "input_dir_size": get_directory_size(config.INPUT_DIR),
            "output_dir_size": get_directory_size(config.OUTPUT_DIR),
            "logs_dir_size": get_directory_size(config.LOGS_DIR),
        })

    return stats

def get_directory_size(path: Path) -> str:
    """
    Verilen dizindeki tüm dosyaların toplam boyutunu MB cinsinden döner.
    """
    total_size = 0  # total_size_ yerine total_size
    for file_path in path.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    
    return f"{total_size / (1024 * 1024):.2f} MB"  # total_size_ yerine total_size
