import json
import asyncio
import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, Text
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from thefuzz import process, fuzz
from dotenv import load_dotenv

load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST")
WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}" if WEBHOOK_HOST else None
WEB_SERVER_HOST = "0.0.0.0"
WEB_SERVER_PORT = int(os.getenv("PORT", 8080))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

with open('heroes.json', 'r', encoding='utf-8') as f:
    heroes_data = json.load(f)
heroes_list = list(heroes_data.keys())

# Постоянная клавиатура с кнопкой "Список персонажей"
list_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Список персонажей")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Это бот с билдами для League of Legends: Wild Rift.\nНажми 'Список персонажей' или введи имя/номер героя:",
        reply_markup=list_keyboard
    )

@dp.message(Text("Список персонажей"))
async def handle_list_heroes(message: types.Message):
    heroes_text = "Список персонажей LoL Wild Rift:\n" + "\n".join(
        f"{i+1}. {hero}" for i, hero in enumerate(heroes_list)
    )
    await message.reply(
        f"{heroes_text}\n\nВведи номер или название персонажа:",
        reply_markup=list_keyboard
    )

@dp.message()
async def handle_hero_choice(message: types.Message):
    user_input = message.text.strip()
    try:
        hero_index = int(user_input) - 1
        if 0 <= hero_index < len(heroes_list):
            hero_name = heroes_list[hero_index]
        else:
            await message.reply("Неверный номер персонажа! Введи номер или название:", reply_markup=list_keyboard)
            return
    except ValueError:
        if user_input != "Список персонажей":
            match = process.extractOne(user_input, heroes_list, scorer=fuzz.token_sort_ratio)
            if match and match[1] >= 70:
                hero_name = match[0]
            else:
                await message.reply("Персонаж не найден! Проверь написание или введи номер:", reply_markup=list_keyboard)
                return
        else:
            return

    hero = heroes_data[hero_name]
    build_text = (
        f"{hero_name}:\n\n"
        f"Роль: {hero['r']}\n\n"
        f"Предметы:\n{hero['i']}\n\n"
        f"Руны:\n{hero['u']}\n\n"
        f"Порядок скиллов:\n{hero['s']}\n\n"
        f"Советы:\n{hero['t']}"
    )
    await message.reply(build_text, reply_markup=list_keyboard)

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
    await bot.session.close()
    logging.info("Bot session closed")

async def main():
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    if WEBHOOK_URL:
        app = web.Application()
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
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    app = loop.run_until_complete(main())
    if app:
        try:
            web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)
        finally:
            loop.close()
