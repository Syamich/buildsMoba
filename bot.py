import json
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from thefuzz import process, fuzz
from dotenv import load_dotenv
import os

# Загрузка токена из переменной окружения
load_dotenv()
API_TOKEN = os.getenv("BOT_TOKEN")

# Инициализация бота
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Загрузка данных из JSON
with open('heroes.json', 'r', encoding='utf-8') as f:
    heroes_data = json.load(f)
heroes_list = list(heroes_data.keys())

# Создание клавиатуры с выбором игры
game_keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
game_keyboard.add(KeyboardButton("Dota 2"), KeyboardButton("LoL"))

# Обработчик команды /start
@dp.message(Command("start"))
async def send_welcome(message: types.Message):
    await message.reply(
        "Привет! Выбери игру:",
        reply_markup=game_keyboard
    )

# Обработчик выбора игры
@dp.message(lambda message: message.text in ["Dota 2", "LoL"])
async def handle_game_choice(message: types.Message):
    if message.text == "Dota 2":
        # Формируем пронумерованный список персонажей
        heroes_text = "Список персонажей Dota 2:\n" + "\n".join(
            f"{i+1}. {hero}" for i, hero in enumerate(heroes_list)
        )
        await message.reply(
            f"{heroes_text}\n\nВведи номер или название персонажа:",
            reply_markup=types.ReplyKeyboardRemove()
        )
    else:
        await message.reply("Поддержка LoL будет добавлена позже. Выбери Dota 2!", reply_markup=game_keyboard)

# Обработчик выбора персонажа
@dp.message()
async def handle_hero_choice(message: types.Message):
    user_input = message.text.strip()
    
    # Проверяем, является ли ввод числом
    try:
        hero_index = int(user_input) - 1
        if 0 <= hero_index < len(heroes_list):
            hero_name = heroes_list[hero_index]
        else:
            await message.reply("Неверный номер персонажа! Введи номер или название персонажа:")
            return
    except ValueError:
        # Если не число, ищем по названию с учётом орфографии
        match = process.extractOne(user_input, heroes_list, scorer=fuzz.token_sort_ratio)
        if match and match[1] >= 70:  # Порог совпадения 70%
            hero_name = match[0]
        else:
            await message.reply("Персонаж не найден! Проверь написание или введи номер:")
            return

    # Формируем билд
    hero = heroes_data[hero_name]
    build_text = (
        f"{hero_name}:\n\n"
        f"Роль: {hero['role']}\n\n"
        f"Предметы:\n{hero['items']}\n\n"
        f"Таланты:\n{hero['talents']}\n"
        f"Порядок скиллов:\n{hero['skill_order']}\n\n"
        f"Советы:\n{hero['tips']}"
    )
    await message.reply(build_text)

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
