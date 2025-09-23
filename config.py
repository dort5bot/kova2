"""bot/config.py - Aiogram 3.x uyumlu optimal config yönetimi

Binance ve Aiogram için yapılandırma sınıfı. Default değerler ile gelir,
.env dosyasındaki değerlerle override edilir.
"""

import os
import logging
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from dotenv import load_dotenv

# Environment variables'ı yükle
load_dotenv()

# Logging yapılandırması
logger = logging.getLogger(__name__)
logger.setLevel(logging.getLevelName(os.getenv("LOG_LEVEL", "INFO")))

# Global cache instance
_CONFIG_INSTANCE: Optional["BotConfig"] = None


@dataclass
class OnChainConfig:
    GLASSNODE_API_KEY: str = field(default_factory=lambda: os.getenv("GLASSNODE_API_KEY", "your_glassnode_api_key_here"))
    METRIC_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "stablecoin_supply_ratio": 0.3,
        "exchange_net_flow": 0.3,
        "etf_flows": 0.2,
        "fear_greed_index": 0.2
    })
    SSR_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: {
        "bearish": 20.0,
        "bullish": 5.0,
        "neutral": 10.0
    })
    NETFLOW_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: {
        "bearish": 1000,
        "bullish": -1000
    })
    ETF_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: {
        "max_flow": 50000000
    })
    API_TIMEOUTS: Dict[str, int] = field(default_factory=lambda: {
        "glassnode": 30,
        "fear_greed": 10,
        "binance": 15
    })
    CACHE_TTL: Dict[str, int] = field(default_factory=lambda: {
        "ssr": 3600,
        "netflow": 1800,
        "etf_flows": 3600,
        "fear_greed": 3600
    })
    FALLBACK_VALUES: Dict[str, float] = field(default_factory=lambda: {
        "ssr": 0.0,
        "netflow": 0.0,
        "etf_flows": 0.0,
        "fear_greed": 0.0
    })


@dataclass
class AnalysisConfig:
    """Analiz modülü konfigürasyonu"""
    # Cache ayarları
    ANALYSIS_CACHE_TTL: int = field(default_factory=lambda: int(os.getenv("ANALYSIS_CACHE_TTL", "60")))
    MAX_CACHE_SIZE: int = field(default_factory=lambda: int(os.getenv("MAX_CACHE_SIZE", "1000")))
    
    # Skor threshold'ları
    SIGNAL_THRESHOLDS: Dict[str, float] = field(default_factory=lambda: {
        "strong_bull": 0.7,
        "bull": 0.3, 
        "bear": -0.3,
        "strong_bear": -0.7
    })
    
    # Modül ağırlıkları
    MODULE_WEIGHTS: Dict[str, float] = field(default_factory=lambda: {
        "tremo": 0.20,
        "regime": 0.18,
        "derivs": 0.16,
        "causality": 0.14,
        "orderflow": 0.12,
        "onchain": 0.10,
        "risk": 0.10
    })
    
    # Timeout ayarları
    MODULE_TIMEOUTS: Dict[str, int] = field(default_factory=lambda: {
        "causality": 30,
        "derivs": 25,
        "onchain": 40,
        "orderflow": 20,
        "regime": 35,
        "tremo": 30,
        "risk": 25
    })
    
    # Risk yönetimi
    MIN_CONFIDENCE: float = field(default_factory=lambda: float(os.getenv("MIN_CONFIDENCE", "0.3")))
    MAX_POSITION_SIZE: float = field(default_factory=lambda: float(os.getenv("MAX_POSITION_SIZE", "0.1")))


@dataclass
class BotConfig:
    """Aiogram 3.x uyumlu bot yapılandırma sınıfı."""
    
    # ========================
    # 🤖 TELEGRAM BOT SETTINGS
    # ========================
    TELEGRAM_TOKEN: str = field(default_factory=lambda: os.getenv("TELEGRAM_TOKEN", ""))
    NGROK_URL: str = field(default_factory=lambda: os.getenv("NGROK_URL", "https://2fce5af7336f.ngrok-free.app"))
    
    DEFAULT_LOCALE: str = field(default_factory=lambda: os.getenv("DEFAULT_LOCALE", "en"))
    ADMIN_IDS: List[int] = field(default_factory=lambda: [
        int(x.strip()) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()
    ])
    
    # Webhook settings
    USE_WEBHOOK: bool = field(default_factory=lambda: os.getenv("USE_WEBHOOK", "false").lower() == "true")
    WEBHOOK_HOST: str = field(default_factory=lambda: os.getenv("WEBHOOK_HOST", ""))
    WEBHOOK_SECRET: str = field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", ""))
    WEBAPP_HOST: str = field(default_factory=lambda: os.getenv("WEBAPP_HOST", "0.0.0.0"))
    WEBAPP_PORT: int = field(default_factory=lambda: int(os.getenv("PORT", "3000")))
    
    # Aiogram specific settings
    AIOGRAM_REDIS_HOST: str = field(default_factory=lambda: os.getenv("AIOGRAM_REDIS_HOST", "localhost"))
    AIOGRAM_REDIS_PORT: int = field(default_factory=lambda: int(os.getenv("AIOGRAM_REDIS_PORT", "6379")))
    AIOGRAM_REDIS_DB: int = field(default_factory=lambda: int(os.getenv("AIOGRAM_REDIS_DB", "0")))
    
    # FSM storage settings
    USE_REDIS_FSM: bool = field(default_factory=lambda: os.getenv("USE_REDIS_FSM", "true").lower() == "true")
    FSM_STORAGE_TTL: int = field(default_factory=lambda: int(os.getenv("FSM_STORAGE_TTL", "3600")))
    
    # ========================
    # 🔐 BINANCE API SETTINGS
    # ========================
    BINANCE_API_KEY: str = field(default_factory=lambda: os.getenv("BINANCE_API_KEY", ""))
    BINANCE_API_SECRET: str = field(default_factory=lambda: os.getenv("BINANCE_API_SECRET", ""))
    BINANCE_BASE_URL: str = field(default_factory=lambda: os.getenv("BINANCE_BASE_URL", "https://api.binance.com"))
    BINANCE_FAPI_URL: str = field(default_factory=lambda: os.getenv("BINANCE_FAPI_URL", "https://fapi.binance.com"))
    BINANCE_WS_URL: str = field(default_factory=lambda: os.getenv("BINANCE_WS_URL", "wss://stream.binance.com:9443/ws"))

    # ========================
    # ⚙️ TECHNICAL SETTINGS
    # ========================
    DEBUG: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    LOG_LEVEL: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    
    # Rate limiting
    # Devre kesici ayarları
    CIRCUIT_BREAKER_FAILURE_THRESHOLD: int = field(default_factory=lambda: int(os.getenv("FAILURE_THRESHOLD", "5")))
    CIRCUIT_BREAKER_RESET_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("RESET_TIMEOUT", "30")))
    CIRCUIT_BREAKER_HALF_OPEN_TIMEOUT: int = field(default_factory=lambda: int(os.getenv("HALF_OPEN_TIMEOUT", "15")))

    # On-chain analiz için alt config nesnesi
    ONCHAIN: OnChainConfig = field(default_factory=OnChainConfig)

    # Analiz için alt config nesnesi
    ANALYSIS: AnalysisConfig = field(default_factory=AnalysisConfig)
    
    # Database settings
    DATABASE_URL: str = field(default_factory=lambda: os.getenv("DATABASE_URL", ""))
    USE_DATABASE: bool = field(default_factory=lambda: os.getenv("USE_DATABASE", "false").lower() == "true")
    
    # Cache settings
    CACHE_TTL: int = field(default_factory=lambda: int(os.getenv("CACHE_TTL", "300")))
    MAX_CACHE_SIZE: int = field(default_factory=lambda: int(os.getenv("MAX_CACHE_SIZE", "1000")))

    # Analytics specific settings
    CAUSALITY_WINDOW: int = field(default_factory=lambda: int(os.getenv("CAUSALITY_WINDOW", "100")))
    CAUSALITY_MAXLAG: int = field(default_factory=lambda: int(os.getenv("CAUSALITY_MAXLAG", "2")))
    CAUSALITY_CACHE_TTL: int = field(default_factory=lambda: int(os.getenv("CAUSALITY_CACHE_TTL", "10")))
    CAUSALITY_TOP_ALTCOINS: List[str] = field(default_factory=lambda: [
        symbol.strip() for symbol in os.getenv(
            "CAUSALITY_TOP_ALTCOINS", 
            "BNBUSDT,ADAUSDT,SOLUSDT,XRPUSDT,DOTUSDT"
        ).split(",") if symbol.strip()
    ])

    # ========================
    # 📊 TRADING SETTINGS
    # ========================
    SCAN_SYMBOLS: List[str] = field(default_factory=lambda: [
        symbol.strip() for symbol in os.getenv(
            "SCAN_SYMBOLS", 
            "BTCUSDT,ETHUSDT,BNBUSDT,SOLUSDT,TRXUSDT,CAKEUSDT,SUIUSDT,PEPEUSDT,ARPAUSDT,TURBOUSDT"
        ).split(",") if symbol.strip()
    ])
    
    ENABLE_TRADING: bool = field(default_factory=lambda: os.getenv("ENABLE_TRADING", "false").lower() == "true")
    TRADING_STRATEGY: str = field(default_factory=lambda: os.getenv("TRADING_STRATEGY", "conservative"))
    MAX_LEVERAGE: int = field(default_factory=lambda: int(os.getenv("MAX_LEVERAGE", "3")))
    
    # Alert settings
    ALERT_PRICE_CHANGE_PERCENT: float = field(default_factory=lambda: float(os.getenv("ALERT_PRICE_CHANGE_PERCENT", "5.0")))
    ENABLE_PRICE_ALERTS: bool = field(default_factory=lambda: os.getenv("ENABLE_PRICE_ALERTS", "true").lower() == "true")
    ALERT_COOLDOWN: int = field(default_factory=lambda: int(os.getenv("ALERT_COOLDOWN", "300")))

    # ========================
    # 🛠️ METHODS & PROPERTIES
    # ========================

    @property
    def BINANCE_API_CONFIG(self) -> Dict[str, Any]:
        """Binance API için config dict'i"""
        return {
            "api_key": self.BINANCE_API_KEY,
            "api_secret": self.BINANCE_API_SECRET,
            "base_url": self.BINANCE_BASE_URL,
            "fapi_url": self.BINANCE_FAPI_URL,
            "cache_ttl": self.CACHE_TTL,
            "failure_threshold": self.CIRCUIT_BREAKER_FAILURE_THRESHOLD,
            "reset_timeout": self.CIRCUIT_BREAKER_RESET_TIMEOUT
        }
    
    
    
    @property
    def WEBHOOK_PATH(self) -> str:
        """Webhook path'i dinamik olarak oluşturur (Telegram formatına uygun)."""
        if not self.TELEGRAM_TOKEN:
            return "/webhook/default"
        return f"/webhook/{self.TELEGRAM_TOKEN}"

    @property
    def WEBHOOK_URL(self) -> str:
        """Webhook URL'ini döndürür. Sadece USE_WEBHOOK=True ise anlamlı değer üretir."""
        if not self.USE_WEBHOOK or not self.WEBHOOK_HOST:
            return ""
        return f"{self.WEBHOOK_HOST.rstrip('/')}{self.WEBHOOK_PATH}"

    @classmethod
    def load(cls) -> "BotConfig":
        """Environment'dan config yükler."""
        return cls()

    def validate(self) -> bool:
        """Config değerlerini doğrular. Hata durumunda kontrollü çıkış yapar."""
        errors = []
        
        # Telegram bot validation
        if not self.TELEGRAM_TOKEN:
            errors.append("❌ TELEGRAM_TOKEN gereklidir")
        
        # Webhook validation (eğer webhook kullanılıyorsa)
        if self.USE_WEBHOOK:
            if not self.WEBHOOK_HOST:
                errors.append("❌ WEBHOOK_HOST gereklidir (USE_WEBHOOK=true)")
        
        # Binance validation (eğer trading enabled ise)
        if self.ENABLE_TRADING:
            if not self.BINANCE_API_KEY:
                errors.append("❌ BINANCE_API_KEY gereklidir (trading enabled)")
            if not self.BINANCE_API_SECRET:
                errors.append("❌ BINANCE_API_SECRET gereklidir (trading enabled)")
        
        if errors:
            logger.critical("Config validation hatası:\n%s", "\n".join(errors))
            sys.exit(1)
        
        return True

    def is_admin(self, user_id: int) -> bool:
        """Kullanıcının admin olup olmadığını kontrol eder."""
        return user_id in self.ADMIN_IDS

    def to_dict(self, include_sensitive: bool = False) -> Dict[str, Any]:
        """Config'i dict olarak döndürür (debug/log amaçlı).
        
        Args:
            include_sensitive: Hassas bilgileri gösterilsin mi? (default: False)
        """
        sensitive_fields = {"TELEGRAM_TOKEN", "BINANCE_API_KEY", "BINANCE_API_SECRET", "WEBHOOK_SECRET"}
        result = {}
        
        for field_name in self.__dataclass_fields__:
            value = getattr(self, field_name)
            if field_name in sensitive_fields and value and not include_sensitive:
                result[field_name] = "***HIDDEN***"
            else:
                result[field_name] = value
        
        # Property'leri de ekle
        result["WEBHOOK_PATH"] = self.WEBHOOK_PATH
        result["WEBHOOK_URL"] = self.WEBHOOK_URL
        
        return result

    def to_safe_dict(self) -> Dict[str, Any]:
        """Güvenli config dict'i (hassas bilgiler olmadan)."""
        return self.to_dict(include_sensitive=False)


def reload_config() -> BotConfig:
    """Config'i yeniden yükler ve cache'i temizler."""
    global _CONFIG_INSTANCE
    _CONFIG_INSTANCE = None
    logger.info("🔄 Config cache temizlendi, yeniden yükleniyor...")
    return get_config_sync()


def get_config_sync() -> BotConfig:
    """Sync config instance'ını döndürür."""
    global _CONFIG_INSTANCE
    if _CONFIG_INSTANCE is None:
        _CONFIG_INSTANCE = BotConfig.load()
        _CONFIG_INSTANCE.validate()
        logger.info("✅ Bot config yüklendi ve doğrulandı")
        
        # Debug log'da sadece güvenli bilgileri göster
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Config (güvenli): {_CONFIG_INSTANCE.to_safe_dict()}")
    
    return _CONFIG_INSTANCE


async def get_config() -> BotConfig:
    """Global config instance'ını döndürür (async wrapper)."""
    return get_config_sync()


def get_telegram_token() -> str:
    """Aiogram için Telegram bot token'ını döndürür."""
    config = get_config_sync()
    return config.TELEGRAM_TOKEN


def get_admins() -> List[int]:
    """Admin kullanıcı ID'lerini döndürür."""
    config = get_config_sync()
    return config.ADMIN_IDS


def get_webhook_config() -> Dict[str, Any]:
    """Webhook konfigürasyonu döndürür."""
    config = get_config_sync()
    return {
        "path": config.WEBHOOK_PATH,
        "url": config.WEBHOOK_URL,
        "secret_token": config.WEBHOOK_SECRET,
        "host": config.WEBAPP_HOST,
        "port": config.WEBAPP_PORT,
        "enabled": config.USE_WEBHOOK,
    }


def get_redis_config() -> Dict[str, Any]:
    """Aiogram için Redis konfigürasyonu döndürür."""
    config = get_config_sync()
    return {
        "host": config.AIOGRAM_REDIS_HOST,
        "port": config.AIOGRAM_REDIS_PORT,
        "db": config.AIOGRAM_REDIS_DB,
    }