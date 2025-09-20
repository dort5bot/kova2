#Mail Gönderici (utils/mailer.py)
# Mailer Kodunu Güncelleyin (Detaylı Loglama):
"""
Gönderen adrese görünen isim eklendi: Excel Bot <user@domain.com>
Mail header’larına X-Priority ve X-Mailer eklendi
Hem plain text hem HTML body eklendi (modern e-posta uyumu için)
Gmail spam'e düşürüyorsa, farklı bir SMTP servisi deneyin:
Yandex Mail (smtp.yandex.com)
Outlook/Hotmail (smtp-mail.outlook.com)
ojmkrjzsxcxrpzuh
"""
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from config import config
from utils.logger import logger
import ssl

async def send_email_with_attachment(
    to_emails: list,
    subject: str,
    body: str,
    attachment_path: Path,
    max_retries: int = 2
) -> bool:
    """E-posta gönderir (ekli dosya ile) - DETAYLI LOGLAMALI"""
    if not to_emails or not any(to_emails):
        logger.warning("Alıcı email adresi yok")
        return False
    
    # SSL context oluştur
    ssl_context = ssl.create_default_context()
    
    successful = False
    
    for port in config.SMTP_PORTS:
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"📧 Mail gönderimi deneniyor: {to_emails}, Port: {port}, Deneme: {attempt + 1}")
                
                message = MIMEMultipart()
                message["From"] = config.SMTP_USERNAME
                message["To"] = ", ".join(to_emails)
                message["Subject"] = subject
                
                # Mesaj gövdesi
                message.attach(MIMEText(body, "plain", "utf-8"))
                
                # Dosya eki
                if attachment_path.exists():
                    file_size = attachment_path.stat().st_size / 1024  # KB
                    logger.info(f"📎 Eklenecek dosya: {attachment_path.name} ({file_size:.1f} KB)")
                    
                    with open(attachment_path, "rb") as f:
                        attachment = MIMEApplication(f.read(), _subtype="xlsx")
                        attachment.add_header(
                            "Content-Disposition",
                            "attachment",
                            filename=attachment_path.name
                        )
                        message.attach(attachment)
                else:
                    logger.warning(f"❌ Eklenecek dosya bulunamadı: {attachment_path}")
                    return False
                
                # PORT'A GÖRE BAĞLANTI AYARLARI
                use_tls = port == 465  # 465 için SSL, 587 için STARTTLS
                
                logger.info(f"🔌 SMTP bağlantısı: {config.SMTP_SERVER}:{port} (TLS: {use_tls})")
                
                if port == 465:
                    # SSL bağlantısı
                    async with aiosmtplib.SMTP(
                        hostname=config.SMTP_SERVER,
                        port=port,
                        use_tls=True,
                        tls_context=ssl_context
                    ) as server:
                        await server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                        await server.send_message(message)
                
                else:  # port 587
                    # STARTTLS bağlantısı
                    async with aiosmtplib.SMTP(
                        hostname=config.SMTP_SERVER,
                        port=port,
                        use_tls=False
                    ) as server:
                        await server.starttls(tls_context=ssl_context)
                        await server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
                        await server.send_message(message)
                
                logger.info(f"✅ Mail BAŞARIYLA gönderildi: {to_emails}")
                successful = True
                break  # Başarılı oldu, diğer portları deneme
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ Mail gönderme hatası (Port: {port}, Deneme: {attempt + 1}): {error_msg}")
                
                # Son denemede logla
                if attempt == max_retries:
                    logger.error(f"❌ Port {port} için tüm denemeler başarısız")
                
                # Bekle ve tekrar dene
                if attempt < max_retries:
                    wait_time = 2 ** attempt
                    import asyncio
                    await asyncio.sleep(wait_time)
        
        if successful:
            break  # Başarılı oldu, diğer portları deneme
    
    if not successful:
        logger.error(f"❌❌❌ TÜM MAIL GÖNDERME DENEMELERİ BAŞARISIZ: {to_emails}")
    
    return successful