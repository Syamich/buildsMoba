import json
import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from thefuzz import process, fuzz
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")  # Set on Render, e.g., https://buildsmoba.onrender.com
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))  # Render sets PORT

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

with open('heroes.json', 'r', encoding='utf-8') as f:
    heroes_data = json.load(f)
heroes_list = list(heroes_data.keys())

# Создаём клавиатуру как список списков
game_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Dota 2"), KeyboardButton(text="LoL")]
    ],
    resize_keyboard=True
)

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Выбери игру:",
        reply_markup=game_keyboard
    )

@dp.message(lambda message: message.text in ["Dota 2", "LoL"])
async def handle_game_choice(message: types.Message):
    if message.text == "Dota 2":
        heroes_text = "Список персонажей Dota 2:\n" + "\n".join(
            f"{i+1}. {hero}" for i, hero in enumerate(heroes_list)
        )
        await message.reply(
            f"{heroes_text}\n\nВведи номер или название персонажа:",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.reply("Поддержка LoL будет добавлена позже. Выбери Dota 2!", reply_markup=game_keyboard)

@dp.message()
async def handle_hero_choice(message: types.Message):
    user_input = message.text.strip()
    try:
        hero_index = int(user_input) - 1
        if 0 <= hero_index < len(heroes_list):
            hero_name = heroes_list[hero_index]
        else:
            await message.reply("Неверный номер персонажа! Введи номер или название персонажа:")
            return
    except ValueError:
        match = process.extractOne(user_input, heroes_list, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 70:
            hero_name = match[0]
        else:
            await message.reply("Персонаж не найден! Проверь написание или введи номер:")
            return

    hero = heroes_data[hero_name]
    build_text = (
        f"{hero_name}:\n\n"
        f"Роль: {hero['role']}\n\n"
        f"Предметы:\n{hero['items']}\n\n"
        f"Таланты:\n{hero['talents']}\n"
        f"Порядок скиллов:\n{hero['skill_order']}\n\n"
        f"Советы: {hero['tips']}"
    )
    await message.reply(build_text)

# Health check эндпоинт для Render
async def health_check(request):
    return web.Response(status=200, text="OK")

async def on_startup(bot: Bot) -> None:
    if WEBHOOK_URL:
        await bot.delete_webhook()
        await bot.set_webhook(WEBHOOK_URL)
        logging.info(f"Webhook set to {WEBHOOK_URL}")
    else:
        logging.info("Starting in polling mode")

async def on_shutdown(bot: Bot) -> None:
    # Не удаляем вебхук, чтобы избежать сброса при перезапусках
    await bot.session.close()
    logging.info("Bot session closed")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    if WEBHOOK_URL:
        app = web.Application()
        # Добавляем health check эндпоинт
        app.router.add_get("/", health_check)
        webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
        webhook_requests_handler.register(app, path=WEBHOOK_PATH)
        setup_application(app, dp, bot=bot)
        logging.info("Starting webhook server")
        return app
    else:
        logging.info("Starting polling")
        await dp.start_polling(bot)

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(main())
    if app:
        web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
