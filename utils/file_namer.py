#Dosya İsimlendirici (utils/file_namer.py)
from datetime import datetime
from typing import Dict

def generate_output_filename(group_info: Dict) -> str:
    """Çıktı dosyası için isim oluşturur"""
    group_id = group_info.get("group_id", "Grup_0")
    group_name = group_info.get("group_name", "")
    
    timestamp = datetime.now().strftime("%m%d_%H%M")
    
    if group_name and group_name != group_id:
        filename = f"{group_name}-{timestamp}.xlsx"
    else:
        filename = f"{group_id}-{timestamp}.xlsx"
    
    return filename
