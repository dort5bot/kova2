#KOVA   main.py
#
import asyncio
import os
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

from config import config
from handlers.reply_handler import router as reply_router
from handlers.upload_handler import router as upload_router
from handlers.status_handler import router as status_router
from handlers.admin_handler import router as admin_router
from handlers.dar_handler import router as dar_router
from handlers.id_handler import router as id_router
from handlers.json_handler import router as json_router
from handlers.file_handler import router as file_router
from handlers.tek_handler import router as tek_router
from handlers.cancel_handler import router as cancel_router




from utils.logger import setup_logger

# Logger kurulumu
setup_logger()

# Health check ve webhook için farklı portlar
HEALTH_CHECK_PORT = 8080  # Health check için varsayılan port
WEBHOOK_PORT = config.PORT  # Webhook için config'ten gelen port


async def handle_health_check(reader, writer):
    """Asenkron health check handler"""
    try:
        # İsteği oku
        data = await reader.read(1024)
        if not data:
            return

        # Basit HTTP isteği parsing
        request_line = data.decode().split('\r\n')[0]
        method, path, _ = request_line.split()
        
        if path == '/health':
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: text/plain\r\n"
                "Content-Length: 13\r\n\r\n"
                "Bot is running"
            )
            writer.write(response.encode())
            await writer.drain()
        else:
            response = (
                "HTTP/1.1 404 Not Found\r\n"
                "Content-Type: text/plain\r\n\r\n"
                "Not Found"
            )
            writer.write(response.encode())
            await writer.drain()
    except Exception as e:
        print(f"Health check hatası: {e}")
        try:
            response = (
                "HTTP/1.1 500 Internal Server Error\r\n"
                "Content-Type: text/plain\r\n\r\n"
                "Error"
            )
            writer.write(response.encode())
            await writer.drain()
        except Exception:
            pass
    finally:
        writer.close()
        await writer.wait_closed()


async def start_health_check_server(port: int):
    """Asenkron health check sunucusu başlat"""
    server = await asyncio.start_server(
        handle_health_check, 
        "0.0.0.0", 
        port
    )
    print(f"✅ Health check sunucusu {port} portunda başlatıldı")
    return server


# -------------------------------
# Webhook mode için aiohttp server
# -------------------------------
async def webhook_handler(request: web.Request):
    """Telegram'dan gelen update'leri aiogram'a aktarır"""
    dp: Dispatcher = request.app["dp"]
    bot: Bot = request.app["bot"]
    
    # Secret token kontrolü (eğer ayarlanmışsa)
    if config.WEBHOOK_SECRET:
        token = request.headers.get('X-Telegram-Bot-Api-Secret-Token')
        if token != config.WEBHOOK_SECRET:
            return web.Response(status=403, text="Forbidden")
    
    try:
        update = await request.json()
        await dp.feed_webhook_update(bot, update)
        return web.Response(text="ok")
    except Exception as e:
        print(f"Webhook hata: {e}")
        return web.Response(status=500, text="error")


async def start_webhook(bot: Bot, dp: Dispatcher):
    """Webhook mode başlatıcı"""
    app = web.Application()
    app["dp"] = dp
    app["bot"] = bot

    # Webhook endpoint'i
    app.router.add_post("/webhook", webhook_handler)
    
    # Health endpoint'i webhook modu için de ekle
    async def health_check(request):
        return web.Response(text="Bot is running")
    
    app.router.add_get("/health", health_check)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", WEBHOOK_PORT)
    print(f"🌐 Webhook sunucusu {WEBHOOK_PORT} portunda dinleniyor (/webhook)")
    await site.start()

    # Telegram'a webhook bildirimi
    await bot.set_webhook(
        url=f"{config.WEBHOOK_URL}/webhook",
        secret_token=config.WEBHOOK_SECRET or None,
        drop_pending_updates=True,
    )
    
    return runner  # Graceful shutdown için runner'ı döndür


async def start_polling(bot: Bot, dp: Dispatcher):
    """Polling mode başlatıcı"""
    print("🤖 Polling modu başlatılıyor...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


# -------------------------------
# Main
# -------------------------------
async def main():
    if not config.TELEGRAM_TOKEN:
        print("❌ HATA: Bot token bulunamadı!")
        return

    storage = MemoryStorage()

    bot = Bot(
        token=config.TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=storage)

    # Router'ları yükle
    dp.include_router(cancel_router)  # cancel_handler
    dp.include_router(reply_router)
    dp.include_router(upload_router)
    dp.include_router(status_router)
    dp.include_router(admin_router)
    dp.include_router(dar_router)
    dp.include_router(id_router)
    dp.include_router(json_router)
    dp.include_router(file_router)
    dp.include_router(tek_router)  # Diğer router'lardan sonra



    health_server = None
    webhook_runner = None

    try:
        # Health check sunucusunu başlat (her iki mod için de)
        health_server = await start_health_check_server(HEALTH_CHECK_PORT)
        health_task = asyncio.create_task(health_server.serve_forever())

        if config.USE_WEBHOOK:
            # Webhook modu
            print("🚀 Webhook modu başlatılıyor...")
            webhook_runner = await start_webhook(bot, dp)
            
            # Her iki sunucu da çalışır durumda kalacak
            await asyncio.Event().wait()
        else:
            # Polling modu
            await start_polling(bot, dp)

    except KeyboardInterrupt:
        print("⚠️  Bot kapatılıyor...")
    except Exception as e:
        print(f"❌ Ana hata: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Graceful shutdown
        print("🔴 Bot durduruluyor...")
        
        if webhook_runner:
            await webhook_runner.cleanup()
        
        if health_server:
            health_server.close()
            await health_server.wait_closed()
        
        await bot.session.close()
        print("✅ Bot başarıyla durduruldu")


if __name__ == "__main__":
    # Asyncio event loop yönetimi
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("✅ Bot kapatıldı")