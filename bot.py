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
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Список персонажей")]],
    resize_keyboard=True,
    one_time_keyboard=False
)

# Клавиатура с персонажами в три колонки
def create_heroes_keyboard():
    keyboard = []
    for i in range(0, len(heroes_list), 3):
        row = [KeyboardButton(text=heroes_list[j]) for j in range(i, min(i + 3, len(heroes_list)))]
        keyboard.append(row)
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=False)

@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Это бот с билдами для League of Legends: Wild Rift.\nНажми 'Список персонажей' или введи имя героя (на русском или английском):",
        reply_markup=main_keyboard
    )

@dp.message(lambda message: message.text == "Список персонажей")
async def handle_list_heroes(message: types.Message):
    await message.reply(
        "Выбери персонажа:",
        reply_markup=create_heroes_keyboard()
    )

@dp.message()
async def handle_hero_choice(message: types.Message):
    user_input = message.text.strip()
    if user_input == "Список персонажей":
        return  # Игнорируем, так как обработано выше
    
    # Словарь для соответствия английских имён русским
    eng_to_rus = {
        "Ahri": "Ари", "Nocturne": "Ноктюрн", "Zilean": "Зайл", "Vi": "Вай", "Sett": "Сетт",
        "Ryze": "Райз", "Leona": "Леона", "Gnar": "Гнар", "Viego": "Виего", "Rumble": "Рамбл",
        "Aatrox": "Атрокс", "Akali": "Акали", "Ashe": "Эш", "Blitzcrank": "Блицкранк",
        "Caitlyn": "Кейтлин", "Draven": "Дрейвен", "Evelynn": "Эвелин", "Garen": "Гарен",
        "Janna": "Джанна", "Jax": "Джакс"
    }
    # Поиск по русскому или английскому имени
    hero_name = None
    if user_input in heroes_list:
        hero_name = user_input
    else:
        # Проверяем английское имя
        for eng, rus in eng_to_rus.items():
            if user_input.lower() == eng.lower():
                hero_name = rus
                break
        if not hero_name:
            # Проверяем по fuzzy-поиску
            match = process.extractOne(user_input, heroes_list, scorer=fuzz.token_sort_ratio)
            if match and match[1] >= 70:
                hero_name = match[0]
            else:
                await message.reply("Персонаж не найден! Проверь написание или выбери из списка:", reply_markup=main_keyboard)
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
    await message.reply(build_text, reply_markup=main_keyboard)

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
