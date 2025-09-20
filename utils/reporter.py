#Rapor Oluşturucu (utils/reporter.py)
from typing import Dict

def generate_processing_report(result: Dict) -> str:
    """İşlem sonrası rapor oluşturur"""
    if not result.get("success", False):
        return "❌ İşlem başarısız oldu."
    
    output_files = result.get("output_files", {})
    total_rows = result.get("total_rows", 0)
    matched_rows = result.get("matched_rows", 0)
    unmatched_rows = total_rows - matched_rows
    
    report_lines = [
        "✅ Dosya işlendi.",
        f"Toplam satır: {total_rows}",
        f"Eşleşen satır: {matched_rows}",
        f"Eşleşmeyen satır: {unmatched_rows}",
        "",
        "Oluşan dosyalar:"
    ]
    
    for group_id, file_info in output_files.items():
        filename = file_info.get("filename", "bilinmeyen")
        row_count = file_info.get("row_count", 0)
        report_lines.append(f"- {filename} ({row_count} satır)")
    
    email_count = sum(1 for file_info in output_files.values() 
                     if file_info.get("email_sent", False))
    
    if email_count > 0:
        report_lines.append(f"")
        report_lines.append(f"📧 Mail gönderildi: {email_count} alıcıya")
    
    return "\n".join(report_lines)
