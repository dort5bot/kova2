# main.py
# kova
# .env → USE_WEBHOOK=true/false ile mod seçiliyor.
import asyncio
import os
import socket
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from config import config
from handlers.upload_handler import router as upload_router
from handlers.status_handler import router as status_router
from handlers.admin_handler import router as admin_router
from handlers.dar_handler import router as dar_router
from handlers.id_handler import router as id_router
from handlers.json_handler import router as json_router
from handlers.buttons.button_handler import router as button_router

from utils.logger import setup_logger

# Logger kurulumu
setup_logger()
import logging
logger = logging.getLogger(__name__)

# -------------------------------
# Webhook mode için aiohttp server
# -------------------------------
async def webhook_handler(request: web.Request):
    """Telegram'dan gelen update'leri aiogram'a aktarır"""
    dp: Dispatcher = request.app["dp"]
    bot: Bot = request.app["bot"]
    try:
        # Webhook secret kontrolü (isteğe bağlı)
        if config.WEBHOOK_SECRET:
            secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
            if secret != config.WEBHOOK_SECRET:
                logger.warning("Geçersiz webhook secret")
                return web.Response(status=403, text="Forbidden")
        
        update = await request.json()
        await dp.feed_webhook_update(bot, update)
        return web.Response(text="ok")
    except Exception as e:
        logger.error(f"Webhook hata: {e}")
        return web.Response(status=500, text="error")

async def handle_health_check(request: web.Request):
    """Health check endpoint"""
    return web.Response(text="Bot is running")

async def start_webhook(bot: Bot, dp: Dispatcher):
    """Webhook mode başlatıcı"""
    app = web.Application()
    app["dp"] = dp
    app["bot"] = bot

    # webhook endpoint -> /webhook/<BOT_TOKEN>
    webhook_path = f"/webhook/{config.TELEGRAM_TOKEN}"
    app.router.add_post(webhook_path, webhook_handler)
    
    # health check endpoint
    app.router.add_get("/health", handle_health_check)
    app.router.add_get("/", handle_health_check)  # root endpoint

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", config.PORT)
    logger.info(f"🌐 Webhook sunucusu {config.PORT} portunda dinleniyor ({webhook_path})")
    await site.start()

    # telegram'a webhook bildir
    webhook_url = f"{config.WEBHOOK_URL}{webhook_path}"
    try:
        await bot.set_webhook(
            url=webhook_url,
            secret_token=config.WEBHOOK_SECRET or None,
            drop_pending_updates=True,
        )
        logger.info(f"✅ Webhook ayarlandı: {webhook_url}")
    except Exception as e:
        logger.error(f"❌ Webhook ayarlanamadı: {e}")

    return runner

# -------------------------------
# Polling modu için health check server
# -------------------------------
async def handle_health_check_socket(reader, writer):
    """Asenkron health check handler (polling modu için)"""
    try:
        await reader.read(1024)  # isteği oku
        response = "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\n\r\nBot is running"
        writer.write(response.encode())
        await writer.drain()
    except Exception as e:
        logger.error(f"Health check hatası: {e}")
    finally:
        writer.close()
        await writer.wait_closed()

async def start_health_check_server(port: int):
    """Asenkron health check sunucusu başlat (polling modu için)"""
    server = await asyncio.start_server(handle_health_check_socket, "0.0.0.0", port)
    logger.info(f"✅ Health check sunucusu {port} portunda başlatıldı")
    return server

# -------------------------------
# Main
# -------------------------------
async def main():
    if not config.TELEGRAM_TOKEN:
        logger.error("❌ HATA: Bot token bulunamadı!")
        return

    storage = MemoryStorage()

    bot = Bot(
        token=config.TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Router'ları yükle
    dp.include_router(upload_router)
    dp.include_router(status_router)
    dp.include_router(admin_router)
    dp.include_router(dar_router)
    dp.include_router(id_router)
    dp.include_router(json_router)
    dp.include_router(button_router)

    try:
        if config.USE_WEBHOOK:
            # Webhook modu
            logger.info("🚀 Webhook modu başlatılıyor...")
            if not config.WEBHOOK_URL:
                logger.error("❌ WEBHOOK_URL tanımlanmamış!")
                return
                
            webhook_runner = await start_webhook(bot, dp)
            
            # Sonsuza kadar çalış
            await asyncio.Event().wait()

        else:
            # Polling modu
            logger.info("🤖 Polling modu başlatılıyor...")
            await bot.delete_webhook(drop_pending_updates=True)
            
            # Health check sunucusu (sadece polling modunda)
            health_server = await start_health_check_server(config.PORT)
            
            async with health_server:
                health_task = asyncio.create_task(health_server.serve_forever())
                try:
                    await dp.start_polling(bot)
                finally:
                    health_task.cancel()
                    try:
                        await health_task
                    except asyncio.CancelledError:
                        pass

    except Exception as e:
        logger.error(f"❌ Ana hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
