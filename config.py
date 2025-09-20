# config.py
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# .env dosyasını yükle
env_path = Path('.') / '.env'
load_dotenv()

# Logger henüz kurulmadığı için temel logging kullan
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Debug amaçlı bazı env değişkenlerini göster
logger.info("Mevcut env değişkenleri:")
for key in ['TELEGRAM_TOKEN', 'ADMIN_CHAT_IDS', 'SMTP_USERNAME', 'USE_WEBHOOK', 'WEBHOOK_URL']:
    value = os.getenv(key)
    if value:
        logger.info(f"  {key}: {value}")
    else:
        logger.warning(f"  {key}: TANIMSIZ")


@dataclass
class Config:
    # -----------------------------
    # Temel Bot Ayarları
    # -----------------------------
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")

    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_PORT: int = int(os.getenv("SMTP_PORT", 587))
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    ADMIN_CHAT_IDS: list[int] = field(default_factory=list)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # -----------------------------
    # Webhook / Polling Ayarları
    # -----------------------------
    # USE_WEBHOOK=true → webhook aktif
    # USE_WEBHOOK=false → polling aktif
    USE_WEBHOOK: bool = field(
        default_factory=lambda: os.getenv("USE_WEBHOOK", "false").lower() == "true"
    )
    WEBHOOK_URL: str = field(
        default_factory=lambda: os.getenv("WEBHOOK_URL", "").rstrip("/")
    )  # Örn: https://abc2.onrender.com
    WEBHOOK_SECRET: str = field(
        default_factory=lambda: os.getenv("WEBHOOK_SECRET", "")
    )
    PORT: int = field(
        default_factory=lambda: int(os.getenv("PORT", "3000"))
    )  # Render/Heroku için port

    def __post_init__(self):
        # -----------------------------
        # Admin Chat ID'leri Yükle
        # -----------------------------
        admin_ids = os.getenv("ADMIN_CHAT_IDS", "")
        logger.info(f"ADMIN_CHAT_IDS raw değer: '{admin_ids}'")

        self.ADMIN_CHAT_IDS = []
        if admin_ids and admin_ids.strip():
            try:
                cleaned = admin_ids.strip()
                if "," in cleaned:
                    ids_list = [int(id_str.strip()) for id_str in cleaned.split(",")]
                else:
                    ids_list = [int(cleaned)]

                self.ADMIN_CHAT_IDS = ids_list
                logger.info(f"✅ Yüklenen Admin ID'leri: {self.ADMIN_CHAT_IDS}")
            except ValueError as e:
                logger.error(f"❌ HATA: Admin ID dönüşüm hatası: {e}")
                logger.error(f"❌ Hatalı değer: '{admin_ids}'")
        else:
            logger.warning("⚠️ ADMIN_CHAT_IDS boş veya tanımlanmamış")

        # Webhook kontrolü
        if self.USE_WEBHOOK and not self.WEBHOOK_URL:
            logger.warning("⚠️ USE_WEBHOOK true ama WEBHOOK_URL boş!")

        # -----------------------------
        # Veri klasörlerini hazırla
        # -----------------------------
        self.DATA_DIR = Path(__file__).parent / "data"
        self.INPUT_DIR = self.DATA_DIR / "input"
        self.OUTPUT_DIR = self.DATA_DIR / "output"
        self.GROUPS_DIR = self.DATA_DIR / "groups"
        self.LOGS_DIR = self.DATA_DIR / "logs"

        for directory in [
            self.DATA_DIR,
            self.INPUT_DIR,
            self.OUTPUT_DIR,
            self.GROUPS_DIR,
            self.LOGS_DIR,
        ]:
            directory.mkdir(parents=True, exist_ok=True)


# Config objesi
config = Config()
