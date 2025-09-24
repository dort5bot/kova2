# config.py KOVA
"""
✅ Otomatik Port Seçimi - Yandex: 465, Gmail: [465, 587]

SMTP_SERVER=smtp.gmail.com  # GMail için:
SMTP_SERVER=smtp.yandex.com # Yandex için:

"""
import os
import logging
from dataclasses import dataclass, field
from pathlib import Path
from dotenv import load_dotenv

# Önce dotenv'i yükle
env_path = Path('.') / '.env'
logging.info(f".env dosya yolu: {env_path.absolute()}")
logging.info(f".env dosyası var mı: {env_path.exists()}")

load_dotenv()

# Tüm env değişkenlerini debug için göster
logging.info("Mevcut env değişkenleri:")
for key in ['TELEGRAM_TOKEN', 'ADMIN_CHAT_IDS', 'USE_WEBHOOK', 'WEBHOOK_URL', 'WEBHOOK_SECRET']:
    value = os.getenv(key)
    if value:
        logging.info(f"  {key}: {value}")
    else:
        logging.warning(f"  {key}: TANIMSIZ")

@dataclass
class Config:
    # Ana bot token - main.py'de TELEGRAM_TOKEN olarak kullanılıyor
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    
    # Webhook ayarları
    USE_WEBHOOK: bool = field(default_factory=lambda: os.getenv("USE_WEBHOOK", "False").lower() == "true")
    WEBHOOK_URL: str = os.getenv("WEBHOOK_URL", "")
    WEBHOOK_SECRET: str = os.getenv("WEBHOOK_SECRET", "")
    
    # Render için port ayarı - main.py'de WEBHOOK_PORT olarak kullanılıyor
    PORT: int = int(os.getenv("PORT", 10000))
    
    # Admin ID'leri
    ADMIN_CHAT_IDS: list[int] = field(default_factory=list)
    
    # tek gönderim maili
    PERSONAL_EMAIL: str = os.getenv("PERSONAL_EMAIL", "dersdep@gmail.com")
    
    
    # SMTP ayarları - AKILLI PORT ALGILAMA - ÇOKLU PORT DESTEĞİ
    SMTP_SERVER: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    SMTP_USERNAME: str = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
    # SMTP_PORTS: list[int] = field(default_factory=lambda: [465, 587])  # ESKİ 2 portlu
    SMTP_PORTS: list[int] = field(default_factory=list)  # YENİ: Boş liste> yandex + gmail için. ALTTA port

    
    
    
    # UTİLS işlemleri için ayarlar
    DEFAULT_EMAIL_RECIPIENTS = ["admin@example.com"]  # Varsayılan email alıcıları
    MAX_EMAIL_RETRIES = 2  # Mail gönderme deneme sayısı
    CHUNK_SIZE = 1000  # Excel işleme chunk boyutu
    LOG_RETENTION_DAYS = 30  # Log tutma süresi
    
    
    
    # Redis (eğer kullanıyorsanız)
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    def __post_init__(self):
        # ADMIN_CHAT_IDS'i yükle
        admin_ids = os.getenv("ADMIN_CHAT_IDS", "")
        logging.info(f"ADMIN_CHAT_IDS raw değer: '{admin_ids}'")
        
        self.ADMIN_CHAT_IDS = []
        if admin_ids and admin_ids.strip():
            try:
                # Çeşitli formatları destekle
                cleaned = admin_ids.strip()
                if ',' in cleaned:
                    ids_list = [int(id_str.strip()) for id_str in cleaned.split(',')]
                else:
                    ids_list = [int(cleaned)]
                
                self.ADMIN_CHAT_IDS = ids_list
                logging.info(f"✅ Yüklenen Admin ID'leri: {self.ADMIN_CHAT_IDS}")
            except ValueError as e:
                logging.error(f"❌ HATA: Admin ID dönüşüm hatası: {e}")
                logging.error(f"❌ Hatalı değer: '{admin_ids}'")
        else:
            logging.warning("⚠️ ADMIN_CHAT_IDS boş veya tanımlanmamış")
        
        
        # SMTP_PORTS'u environment'dan yükle (opsiyonel)
        # AKILLI PORT ALGILAMA
        if not self.SMTP_PORTS:
            if "yandex" in self.SMTP_SERVER.lower():
                self.SMTP_PORTS = [465]  # Yandex sadece 465
            else:
                self.SMTP_PORTS = [465, 587]  # Diğerleri için her iki port
        
        # PERSONAL_EMAIL kontrolü
        if not self.PERSONAL_EMAIL:
            logging.warning("⚠️ PERSONAL_EMAIL tanımlanmamış")
            

        
       # Dizin yapılandırması
        self.DATA_DIR = Path(__file__).parent / "data"
        self.INPUT_DIR = self.DATA_DIR / "input"
        self.OUTPUT_DIR = self.DATA_DIR / "output"
        self.GROUPS_DIR = self.DATA_DIR / "groups"
        self.LOGS_DIR = self.DATA_DIR / "logs"

        for directory in [self.DATA_DIR, self.INPUT_DIR, self.OUTPUT_DIR, self.GROUPS_DIR, self.LOGS_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

config = Config()