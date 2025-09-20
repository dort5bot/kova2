#Mail Gönderici (utils/mailer.py)
import aiosmtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from pathlib import Path
from config import config
from utils.logger import logger

async def send_email_with_attachment(
    to_emails: list,
    subject: str,
    body: str,
    attachment_path: Path
) -> bool:
    """E-posta gönderir (ekli dosya ile)"""
    try:
        message = MIMEMultipart()
        message["From"] = config.SMTP_USERNAME
        message["To"] = ", ".join(to_emails)
        message["Subject"] = subject
        
        # Mesaj gövdesi
        message.attach(MIMEText(body, "plain"))
        
        # Dosya eki
        with open(attachment_path, "rb") as f:
            attachment = MIMEApplication(f.read(), _subtype="xlsx")
            attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=attachment_path.name
            )
            message.attach(attachment)
        
        # SMTP sunucusuna bağlan ve gönder
        """
        async with aiosmtplib.SMTP(
            hostname=config.SMTP_SERVER,
            port=config.SMTP_PORT,
            use_tls=True
        ) as server:
        """
        async with aiosmtplib.SMTP(
            hostname=config.SMTP_SERVER,
            port=config.SMTP_PORT,
            start_tls=True  # ✔️ STARTTLS kullan!
        ) as server:
    
            await server.login(config.SMTP_USERNAME, config.SMTP_PASSWORD)
            await server.send_message(message)
        
        logger.info(f"Mail gönderildi: {to_emails} - {attachment_path.name}")
        return True
        
    except Exception as e:
        logger.error(f"Mail gönderme hatası: {e}")
        return False
