#Rapor Oluşturucu (utils/reporter.py)
from typing import Dict, List
from datetime import datetime
from utils.group_manager import group_manager  # Bu satırı ekleyin

def generate_processing_report(result: Dict) -> str:
    """İşlem sonrası detaylı rapor oluşturur"""
    if not result.get("success", False):
        error_msg = result.get("error", "Bilinmeyen hata")
        return f"❌ İşlem başarısız oldu:\n{error_msg}"
    
    output_files = result.get("output_files", {})
    total_rows = result.get("total_rows", 0)
    matched_rows = result.get("matched_rows", 0)
    unmatched_rows = total_rows - matched_rows
    email_results = result.get("email_results", [])
    user_id = result.get("user_id", "Bilinmeyen")
    
    successful_emails = sum(1 for res in email_results if res.get("success", False))
    failed_emails = len(email_results) - successful_emails
    
    report_lines = [
        "✅ **DOSYA İŞLEME RAPORU**",
        f"⏰ İşlem zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        f"👤 Kullanıcı ID: {user_id}",
        "",
        "📊 **İSTATİSTİKLER:**",
        f"• Toplam satır: {total_rows}",
        f"• Eşleşen satır: {matched_rows}",
        f"• Eşleşmeyen satır: {unmatched_rows}",
        f"• Oluşturulan dosya: {len(output_files)}",
        f"• Başarılı mail: {successful_emails}",
        f"• Başarısız mail: {failed_emails}",
        "",
        "📁 **OLUŞTURULAN DOSYALAR:**"
    ]
    
    for group_id, file_info in output_files.items():
        filename = file_info.get("filename", "bilinmeyen")
        row_count = file_info.get("row_count", 0)
        group_name = group_manager.get_group_info(group_id).get("group_name", group_id)
        report_lines.append(f"• {group_name}: {filename} ({row_count} satır)")
    
    # Eşleşmeyen şehirler
    unmatched_cities = result.get("unmatched_cities", [])
    if unmatched_cities:
        report_lines.extend([
            "",
            "⚠️ **EŞLEŞMEYEN ŞEHİRLER:**",
            f"Toplam {len(unmatched_cities)} farklı şehir:"
        ])
        for city in unmatched_cities[:5]:  # İlk 5 şehir
            report_lines.append(f"• {city}")
        if len(unmatched_cities) > 5:
            report_lines.append(f"• ... ve {len(unmatched_cities) - 5} diğer şehir")
    
    # Mail hataları
    if failed_emails > 0:
        report_lines.extend([
            "",
            "❌ **MAIL GÖNDERİM HATALARI:**"
        ])
        error_count = 0
        for error in email_results:
            if not error.get("success", False) and error_count < 3:
                report_lines.append(f"• {error.get('recipient', 'Bilinmeyen')}: {error.get('error', 'Bilinmeyen hata')}")
                error_count += 1
        if failed_emails > 3:
            report_lines.append(f"• ... ve {failed_emails - 3} diğer hata")
    
    return "\n".join(report_lines)

def generate_email_report(email_results: List[Dict]) -> str:
    """Email gönderim raporu oluşturur"""
    successful = sum(1 for res in email_results if res.get("success", False))
    failed = len(email_results) - successful
    
    report = [
        f"📧 **EMAIL RAPORU**",
        f"✅ Başarılı: {successful}",
        f"❌ Başarısız: {failed}",
        ""
    ]
    
    if failed > 0:
        report.append("**Hatalar:**")
        for i, result in enumerate(email_results[:5], 1):
            if not result.get("success", False):
                report.append(f"{i}. {result.get('recipient', 'Bilinmeyen')}: {result.get('error', 'Bilinmeyen hata')}")
    
    return "\n".join(report)
    

def generate_personal_email_report(result: Dict) -> str:
    """Kişisel mail gönderim raporu oluşturur"""
    if not result.get("success", False):
        error_msg = result.get("error", "Bilinmeyen hata")
        return f"❌ İşlem başarısız oldu:\n{error_msg}"
    
    total_rows = result.get("total_rows", 0)
    email_sent_to = result.get("email_sent_to", "Bilinmeyen")
    user_id = result.get("user_id", "Bilinmeyen")
    
    report_lines = [
        "✅ **KİŞİSEL MAIL GÖNDERİM RAPORU**",
        f"⏰ İşlem zamanı: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        f"👤 Kullanıcı ID: {user_id}",
        "",
        "📊 **İSTATİSTİKLER:**",
        f"• Toplam satır: {total_rows}",
        f"• Gönderilen mail: {email_sent_to}",
        "",
        "📧 **DURUM:** Mail başarıyla gönderildi! ✅"
    ]
    
    return "\n".join(report_lines)