"""
main.py - Telegram Bot Ana Giriş Noktası (FİNAL)
----------------------------------------
Aiogram 3.x + Router pattern + Webhook + Render uyumlu.
- Yeni config yapısına tam uyumlu
- Gelişmiş error handling
- Health check endpoints
- Graceful shutdown
- Local polling desteği eklendi
free tier platformlarla tam uyumludur.
+ (Webhook path now uses /webhook/<BOT_TOKEN> format)
Aiogram 3.x’te Bot sınıfı default olarak data dict’i içermez.
hem lifespan() fonksiyonunda hem de initialize_polling_mode() içinde bot yaratıldıktan hemen sonra şu satırı eklemelisiniz:
bot.data = {}
📌 
2. Bot token sızma riski → Maskeleme iyileştirmesi
/webhook/{token} GET endpoint'inde token'ın sadece ilk ve son birkaç karakteri gösteriliyor. Ancak bir yerde log’lanması hâlinde bu risk olabilir.
🛡️ Öneri: Token'ı direkt olarak hiçbir response içine koymamak daha güvenlidir, ya da sadece sabit "***********" göstermek.

eğer response’lar bir yerde loglanıyorsa, bu endpoint kullanılmaya devam ettikçe sızıntı olabilir.
✅ Ne yapılabilir?
Daha güvenli öneri:

return web.json_response({
    "status": "active",
    "bot_token": "***********",  # veya bu alanı tamamen kaldır
    "method": "POST",
    "message": "Webhook is active. Use POST method for Telegram updates."
})
"""
# main.py başında
import sys
import os
print("=== PYTHON PATH ===")
for path in sys.path:
    print(path)
print("===================")





import os
import asyncio
import logging
import signal
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

import aiohttp
from aiohttp import web
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Update, Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import BaseFilter
from aiogram.types import ErrorEvent

from utils.handler_loader import load_handlers, clear_handler_cache
from utils.binance.binance_a import get_or_create_binance_api  # ✅ DÜZELTME: Factory fonksiyonunu import et
from utils.binance.binance_request import BinanceHTTPClient
from utils.binance.binance_circuit_breaker import CircuitBreaker
from config import BotConfig, get_config, get_telegram_token, get_admins

# ---------------------------------------------------------------------
# Config & Logging Setup
# ---------------------------------------------------------------------
load_dotenv()

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# Global instances
bot: Optional[Bot] = None
dispatcher: Optional[Dispatcher] = None
binance_api: Optional[Any] = None  # ✅ DÜZELTME: Specific type yerine Any
app_config: Optional[BotConfig] = None
runner: Optional[web.AppRunner] = None
polling_task: Optional[asyncio.Task] = None

# Graceful shutdown flag
shutdown_event = asyncio.Event()

# ---------------------------------------------------------------------
# Signal Handling for Graceful Shutdown
# ---------------------------------------------------------------------
def handle_shutdown(signum, frame) -> None:
    """Handle shutdown signals gracefully."""
    logger.info(f"🛑 Received signal {signum}, initiating graceful shutdown...")
    # set the asyncio event in an async-safe way
    try:
        loop = asyncio.get_event_loop()
        loop.call_soon_threadsafe(shutdown_event.set)
    except Exception:
        # If loop closed or unavailable, set directly (best-effort)
        shutdown_event.set()

# Register signal handlers
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

# ---------------------------------------------------------------------
# Error Handler
# ---------------------------------------------------------------------
async def error_handler(event: ErrorEvent) -> None:
    """Global error handler for aiogram."""
    logger.error(f"❌ Error handling update: {event.exception}")
    
    try:
        if getattr(event.update, "message", None):
            await event.update.message.answer("❌ Bir hata oluştu, lütfen daha sonra tekrar deneyin.")
    except Exception as e:
        logger.error(f"❌ Failed to send error message: {e}")

# ---------------------------------------------------------------------
# Rate Limiting Filter
# ---------------------------------------------------------------------
class RateLimitFilter(BaseFilter):
    """Rate limiting filter for messages."""
    
    def __init__(self, rate: float = 1.0):
        self.rate = rate
        self.last_called = 0.0

    async def __call__(self, message: Message) -> bool:
        current_time = asyncio.get_event_loop().time()
        if current_time - self.last_called >= self.rate:
            self.last_called = current_time
            return True
        return False

# ---------------------------------------------------------------------
# Middleware Implementation
# ---------------------------------------------------------------------
class LoggingMiddleware:
    """Middleware for request logging and monitoring."""
    
    async def __call__(self, handler, event, data):
        # Pre-processing
        logger.info(f"📨 Update received: {getattr(event, 'update_id', 'unknown')}")
        start_time = asyncio.get_event_loop().time()
        
        try:
            result = await handler(event, data)
            processing_time = asyncio.get_event_loop().time() - start_time
            logger.info(f"✅ Update processed: {getattr(event, 'update_id', 'unknown')} in {processing_time:.2f}s")
            return result
        except Exception as e:
            logger.error(f"❌ Error processing update {getattr(event, 'update_id', 'unknown')}: {e}")
            raise

class AuthenticationMiddleware:
    """Middleware for user authentication and authorization."""
    
    async def __call__(self, handler, event, data):
        global app_config
        
        # Some events may not have from_user (like callback query wrappers), guard accordingly
        user = getattr(event, "from_user", None)
        if user:
            user_id = user.id
            data['user_id'] = user_id
            data['is_admin'] = app_config.is_admin(user_id) if app_config else False
            logger.debug(f"👤 User {user_id} - Admin: {data['is_admin']}")
        
        return await handler(event, data)

# ---------------------------------------------------------------------
# Dependency Injection Container
# ---------------------------------------------------------------------
class DIContainer:
    """Simple dependency injection container for global instances."""
    
    _instances: Dict[str, Any] = {}
    
    @classmethod
    def register(cls, key: str, instance: Any) -> None:
        """Register an instance with a key."""
        cls._instances[key] = instance
        logger.debug(f"📦 DI Container: Registered {key}")
    
    @classmethod
    def resolve(cls, key: str) -> Optional[Any]:
        """Resolve an instance by key."""
        return cls._instances.get(key)
    
    @classmethod
    def get_all(cls) -> Dict[str, Any]:
        """Get all registered instances."""
        return cls._instances.copy()

# ---------------------------------------------------------------------
# Polling Setup for Local Development
# ---------------------------------------------------------------------
async def start_polling() -> None:
    """Start polling for local development when webhook is not configured."""
    global bot, dispatcher
    
    if not bot or not dispatcher:
        logger.error("❌ Bot or dispatcher not initialized for polling")
        return
    
    try:
        logger.info("🔄 Starting polling mode for local development...")
        # start_polling will run until cancelled
        await dispatcher.start_polling(bot)
    except asyncio.CancelledError:
        logger.info("⏹️ Polling task cancelled")
    except Exception as e:
        logger.error(f"❌ Polling failed: {e}")

# ---------------------------------------------------------------------
# Binance API Initialization Function
# ---------------------------------------------------------------------
async def initialize_binance_api() -> Optional[Any]:
    """
    Initialize Binance API with proper factory pattern.
    
    Returns:
        BinanceAPI instance or None if trading disabled
        
    Raises:
        Exception: If initialization fails
    """
    global app_config
    
    if not app_config.ENABLE_TRADING:
        logger.info("ℹ️ Binance API not initialized (trading disabled)")
        return None
    
    try:
        logger.info("🔄 Initializing Binance API...")
        
        # ✅ DÜZELTME: Factory fonksiyonunu kullan
        binance_api_instance = await get_or_create_binance_api(
            api_key=app_config.BINANCE_API_KEY,
            api_secret=app_config.BINANCE_API_SECRET,
            base_url=app_config.BINANCE_BASE_URL,
            fapi_url=app_config.BINANCE_FAPI_URL,
            cache_ttl=30,
            failure_threshold=getattr(app_config, 'CIRCUIT_BREAKER_FAILURE_THRESHOLD', 5),
            reset_timeout=getattr(app_config, 'CIRCUIT_BREAKER_RESET_TIMEOUT', 30)
        )
        
        logger.info("✅ Binance API initialized successfully")
        return binance_api_instance
        
    except Exception as e:
        logger.error(f"❌ Binance API initialization failed: {e}")
        raise

# ---------------------------------------------------------------------
# Handler Loading with Debug Information
# ---------------------------------------------------------------------
async def initialize_handlers(dispatcher_instance: Dispatcher) -> Dict[str, int]:
    """
    Initialize handlers with comprehensive logging.
    
    Args:
        dispatcher_instance: Dispatcher instance to load handlers into
        
    Returns:
        Loading statistics
    """
    try:
        load_results = await load_handlers(dispatcher_instance)
        
        # ✅ DÜZELTME: Detaylı debug bilgisi
        logger.info(f"📊 Handler yükleme sonuçları: {load_results}")
        
        # Hangi handler'ların yüklendiğini logla
        if dispatcher_instance and hasattr(dispatcher_instance, 'sub_routers'):
            router_names = [getattr(router, 'name', 'unnamed') for router in dispatcher_instance.sub_routers]
            logger.info(f"📋 Yüklenen router'lar: {router_names}")
        
        if load_results.get("failed", 0) > 0:
            logger.warning(f"⚠️ {load_results['failed']} handlers failed to load")
        
        logger.info(f"✅ {load_results.get('loaded', 0)} handlers loaded successfully")
        return load_results
        
    except Exception as e:
        logger.error(f"❌ Handler loading failed: {e}")
        return {"loaded": 0, "failed": 1}

# ---------------------------------------------------------------------
# Lifespan Management (Async Context Manager)
# ---------------------------------------------------------------------
@asynccontextmanager
async def lifespan():
    """Manage application lifecycle with async context manager."""
    global bot, dispatcher, binance_api, app_config, polling_task
    
    try:
        # Load configuration
        app_config = await get_config()
        
        # Initialize bot with default properties
        bot = Bot(
            token=get_telegram_token(),
            default=DefaultBotProperties(
                parse_mode=ParseMode.HTML,
            )
        )
        bot.data = {}   # ✅ FIX: Bot nesnesine data dict ekle
        
        
        # Initialize dispatcher with main router and error handler
        main_router = Router()
        dispatcher = Dispatcher()
        dispatcher.include_router(main_router)
        dispatcher.errors.register(error_handler)
        
        # Register middleware
        dispatcher.update.outer_middleware(LoggingMiddleware())
        dispatcher.update.outer_middleware(AuthenticationMiddleware())
        logger.info("✅ Middleware registered: Logging, Authentication")
        
        # Register instances in DI container
        DIContainer.register('bot', bot)
        DIContainer.register('dispatcher', dispatcher)
        DIContainer.register('config', app_config)
        
        # Initialize Binance API (only if trading is enabled)
        binance_api = await initialize_binance_api()
        
        if binance_api:
            # Binance API'yi bot instance'ına da ekle (handler'lar için)
            bot.data["binance_api"] = binance_api
            DIContainer.register('binance_api', binance_api)
        
        # Load handlers with debug information
        await initialize_handlers(dispatcher)
        
        # Start polling if webhook is not configured (local development)
        if not app_config.USE_WEBHOOK:
            polling_task = asyncio.create_task(start_polling())
            logger.info("✅ Polling mode started for local development")
        
        logger.info("✅ Application components initialized")
        yield
        
    except Exception as e:
        logger.error(f"❌ Application initialization failed: {e}")
        raise
    finally:
        # Cleanup resources
        cleanup_tasks = []
        
        # Cancel polling task if running
        if polling_task and not polling_task.done():
            polling_task.cancel()
            try:
                await polling_task
            except asyncio.CancelledError:
                logger.info("✅ Polling task cancelled successfully")
            except Exception as e:
                logger.warning(f"⚠️ Error cancelling polling task: {e}")
        
        if binance_api:
            cleanup_tasks.append(binance_api.close())
        
        if bot and hasattr(bot, 'session'):
            cleanup_tasks.append(bot.session.close())
        
        # Clear DI container
        DIContainer._instances.clear()
        
        if cleanup_tasks:
            results = await asyncio.gather(*cleanup_tasks, return_exceptions=True)
            for result in results:
                if isinstance(result, Exception):
                    logger.warning(f"⚠️ Cleanup task failed: {result}")
        
        logger.info("🛑 Application resources cleaned up")

# ---------------------------------------------------------------------
# Health Check Endpoints
# ---------------------------------------------------------------------
async def health_check(request: web.Request) -> web.Response:
    """Health check endpoint for Render and monitoring."""
    try:
        services_status = await check_services()

         # Handler durumunu da kontrol et
        handler_status = {
            "total_handlers": len(dispatcher.sub_routers) if dispatcher else 0,
            "handlers_loaded": True if dispatcher and dispatcher.sub_routers else False
        }
        
        return web.json_response({
            "status": "healthy",
            "service": "mbot1-telegram-bot",
            "platform": "render" if "RENDER" in os.environ else ("railway" if "RAILWAY" in os.environ else "local"),
            "timestamp": asyncio.get_event_loop().time(),
            "handlers": handler_status,
            "services": services_status
        })
    except Exception as e:
        return web.json_response({
            "status": "unhealthy",
            "error": str(e)
        }, status=500)

async def readiness_check(request: web.Request) -> web.Response:
    """Readiness check for Kubernetes and load balancers."""
    global bot, binance_api, app_config
    
    if bot and app_config:
        # Binance API is only required if trading is enabled
        if app_config.ENABLE_TRADING and not binance_api:
            return web.json_response({"status": "not_ready"}, status=503)
        
        # Check DI container health
        essential_services = ['bot', 'dispatcher', 'config']
        missing_services = [svc for svc in essential_services if not DIContainer.resolve(svc)]
        
        if missing_services:
            return web.json_response({
                "status": "not_ready",
                "missing_services": missing_services
            }, status=503)
            
        return web.json_response({"status": "ready"})
    else:
        return web.json_response({"status": "not_ready"}, status=503)

async def version_info(request: web.Request) -> web.Response:
    """Version and system information endpoint."""
    return web.json_response(await get_system_info())

# ---------------------------------------------------------------------
# Webhook Setup Functions
# ---------------------------------------------------------------------
async def on_startup(bot: Bot) -> None:
    """Execute on application startup."""
    global app_config
    
    try:
        # Set webhook if webhook is configured
        if app_config.USE_WEBHOOK and app_config.WEBHOOK_HOST:
            # Ensure WEBHOOK_HOST doesn't end with slash
            host = app_config.WEBHOOK_HOST.rstrip("/")
            token = get_telegram_token()
            webhook_url = f"{host}/webhook/{token}"
            await bot.delete_webhook(drop_pending_updates=True)
            
            # set secret_token if provided in config, else None
            secret = getattr(app_config, "WEBHOOK_SECRET", None) or None
            if secret:
                await bot.set_webhook(webhook_url, secret_token=secret)
            else:
                await bot.set_webhook(webhook_url)
            
            logger.info(f"✅ Webhook set successfully: {webhook_url}")
        else:
            logger.info("ℹ️ Webhook not configured, using polling mode")
        
        # Log health check URL (use configured host/port if available)
        try:
            host = app_config.WEBAPP_HOST
            port = app_config.WEBAPP_PORT
            logger.info(f"🌐 Health check: http://{host}:{port}/health")
        except Exception:
            logger.info("🌐 Health check endpoint available at /health")
        
        # 🔔 Adminlere "Bot başlatıldı" mesajı gönder
        for admin_id in get_admins():
            try:
                await bot.send_message(admin_id, "🤖 Bot başlatıldı ve çalışıyor!")
            except Exception as e:
                logger.warning(f"⚠️ Admin {admin_id} mesaj gönderilemedi: {e}")
    
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise

async def on_shutdown(bot: Bot) -> None:
    """Execute on application shutdown."""
    logger.info("🛑 Shutting down application...")
    
    try:
        # Delete webhook if it was set
        if app_config and app_config.USE_WEBHOOK and getattr(app_config, "WEBHOOK_HOST", None):
            try:
                await bot.delete_webhook()
                logger.info("✅ Webhook deleted")
            except Exception as e:
                logger.warning(f"⚠️ Failed to delete webhook: {e}")
    except Exception as e:
        logger.warning(f"⚠️ on_shutdown encountered an error: {e}")

# ---------------------------------------------------------------------
# Main Application Factory
# ---------------------------------------------------------------------
async def create_app() -> web.Application:
    """Create and configure aiohttp web application."""
    global bot, dispatcher, app_config
    
    # Initialize components inside lifespan context
    async with lifespan():
        # Create aiohttp app
        app = web.Application()
        
        # Register routes
        app.router.add_get("/", health_check)
        app.router.add_get("/health", health_check)
        app.router.add_get("/ready", readiness_check)
        app.router.add_get("/version", version_info)
        
        # Configure webhook handler using path /webhook/{token}
        if app_config.USE_WEBHOOK and app_config.WEBHOOK_HOST:
            webhook_handler = SimpleRequestHandler(
                dispatcher=dispatcher,
                bot=bot,
                secret_token=getattr(app_config, "WEBHOOK_SECRET", None) or None
            )
            
            # Use /webhook/{token} pattern
            webhook_route = "/webhook/{token}"
            webhook_handler.register(app, path=webhook_route)
            
            # GET endpoint for basic info/test (verifies token)
            async def webhook_info(request: web.Request):
                token = request.match_info.get('token', '')
                valid_token = get_telegram_token()
                
                if token == valid_token:
                    return web.json_response({
                        "status": "active",
                        "bot_token": "***********",  # Token gizlendi
                        "method": "POST",
                        "message": "Webhook is active. Use POST method for Telegram updates."
                    })
                else:
                    return web.json_response({
                        "status": "invalid_token",
                        "message": "The provided token is invalid."
                    }, status=400)
            
            app.router.add_get(webhook_route, webhook_info)
            logger.info(f"📨 Webhook endpoint configured: {webhook_route}")
        
        # Setup startup/shutdown hooks
        app.on_startup.append(lambda app: on_startup(bot))
        app.on_shutdown.append(lambda app: on_shutdown(bot))
        
        # Setup aiogram application (registers internal routes/handlers)
        setup_application(app, dispatcher, bot=bot)
        
        logger.info(f"🚀 Application configured on port {app_config.WEBAPP_PORT}")
        
        return app

# ---------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------
async def check_services() -> Dict[str, Any]:
    """Check connectivity to all external services."""
    global bot, binance_api, app_config
    
    services_status = {}
    
    # Check Telegram API
    try:
        if bot:
            me = await bot.get_me()
            services_status["telegram"] = {
                "status": "connected",
                "bot_username": me.username,
                "bot_id": me.id,
                "first_name": me.first_name
            }
        else:
            services_status["telegram"] = {"status": "disconnected", "error": "Bot not initialized"}
    except Exception as e:
        services_status["telegram"] = {
            "status": "disconnected",
            "error": str(e)
        }
    
    # Check Binance API (only if trading is enabled)
    if app_config.ENABLE_TRADING:
        try:
            if binance_api:
                ping_result = await binance_api.ping()
                services_status["binance"] = {
                    "status": "connected" if ping_result else "disconnected",
                    "ping": ping_result,
                    "trading_enabled": True
                }
            else:
                services_status["binance"] = {"status": "disconnected", "error": "Binance API not initialized", "trading_enabled": True}
        except Exception as e:
            services_status["binance"] = {
                "status": "disconnected",
                "error": str(e),
                "trading_enabled": True
            }
    else:
        services_status["binance"] = {
            "status": "disabled",
            "trading_enabled": False
        }
    
    return services_status

async def get_system_info() -> Dict[str, Any]:
    """Get system information and status."""
    global app_config
    
    return {
        "version": "1.0.0",
        "platform": "render" if "RENDER" in os.environ else "local",
        "environment": "production" if not app_config.DEBUG else "development",
        "python_version": os.sys.version,
        "aiohttp_version": aiohttp.__version__,
        "debug_mode": app_config.DEBUG,
        "trading_enabled": app_config.ENABLE_TRADING,
        "webhook_enabled": app_config.USE_WEBHOOK,
        "services": await check_services(),
        "di_container_services": list(DIContainer.get_all().keys())
    }

# ---------------------------------------------------------------------
# Polling Mode Initialization
# ---------------------------------------------------------------------
async def initialize_polling_mode() -> None:
    """Initialize and start polling mode."""
    global bot, dispatcher, binance_api, app_config
    
    try:
        # Bot ve Dispatcher oluştur
        bot = Bot(
            token=get_telegram_token(),
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        bot.data = {}   # ✅ FIX: Bot nesnesine data dict ekle
        
        dispatcher = Dispatcher()

        # Middleware ve handler'ları yükle
        dispatcher.update.outer_middleware(LoggingMiddleware())
        dispatcher.update.outer_middleware(AuthenticationMiddleware())
        dispatcher.errors.register(error_handler)

        # Binance API'yi initialize et
        binance_api = await initialize_binance_api()
        
        if binance_api:
            # Binance API'yi bot instance'ına ekle (handler'lar için)
            bot.data["binance_api"] = binance_api
            logger.info("✅ Binance API initialized and added to bot.data")

        # Handler'ları yükle (debug bilgisi ile)
        await initialize_handlers(dispatcher)

        logger.info("✅ Handler ve middleware yüklendi")

        # Webhook sil
        await bot.delete_webhook(drop_pending_updates=True)
        logger.info("✅ Webhook silindi")

        # Polling başlat
        logger.info("🤖 Bot polling modunda başlatılıyor...")
        await dispatcher.start_polling(bot)

    except Exception as e:
        logger.error(f"❌ Polling mode initialization failed: {e}")
        raise

# ---------------------------------------------------------------------
# Main Entry Point
# ---------------------------------------------------------------------
async def main() -> None:
    global app_config, runner, bot, dispatcher

    try:
        # Config yükle
        app_config = await get_config()

        logger.info(f"🏗️ Platform detected: {'Render' if 'RENDER' in os.environ else 'Local'}")
        logger.info(f"🌐 Environment: {'production' if not app_config.DEBUG else 'development'}")
        logger.info(f"🚪 Port: {app_config.WEBAPP_PORT}")
        logger.info(f"🏠 Host: {app_config.WEBAPP_HOST}")
        logger.info(f"🤖 Trading enabled: {app_config.ENABLE_TRADING}")
        logger.info(f"🌐 Webhook mode: {'enabled' if app_config.USE_WEBHOOK else 'disabled (polling)'}")

        if not app_config.USE_WEBHOOK:
            # ✅ POLLING MODU
            await initialize_polling_mode()
        else:
            # ✅ WEBHOOK MODU
            app = await create_app()
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host=app_config.WEBAPP_HOST, port=app_config.WEBAPP_PORT)
            await site.start()

            logger.info(f"✅ Server started on port {app_config.WEBAPP_PORT}")
            logger.info(f"📊 Health check: http://{app_config.WEBAPP_HOST}:{app_config.WEBAPP_PORT}/health")

            await shutdown_event.wait()
            logger.info("👋 Shutdown signal received, exiting...")

    except Exception as e:
        logger.error(f"🚨 Critical error in main(): {e}")
        raise
    finally:
        # Cleanup
        if runner:
            await runner.cleanup()
        if bot and hasattr(bot, 'session'):
            await bot.session.close()
        logger.info("✅ Application cleanup completed")


if __name__ == "__main__":
    # Run the application
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Application terminated by user")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}")
        exit(1)