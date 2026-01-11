import asyncio
import json
import os
import random
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder
from aiogram.exceptions import TelegramBadRequest

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8461545217:AAE-SfSolVZ6Mpx7aGDxQjJX_0JfxaHoXC8"
TMDB_API_KEY = "5e10d0f4cf73c8d9ef282c3d55690d07"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЗАГРУЗКА ДАННЫХ ---
def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"movie": {}, "game": {}, "anime": {}}

DATA = load_data()

# --- КЛАВИАТУРЫ ---

# Главное меню (внизу под полем ввода)
def get_reply_kb():
    builder = ReplyKeyboardBuilder()
    builder.button(text="🎬 Фильм")
    builder.button(text="🎮 Игра")
    builder.button(text="⛩ Аниме")
    builder.adjust(2, 1)
    return builder.as_markup(resize_keyboard=True)

# Кнопки выбора жанров (под сообщением)
def get_genres_kb(content_type):
    builder = InlineKeyboardBuilder()
    if content_type in DATA:
        for genre in DATA[content_type].keys():
            builder.button(text=genre, callback_data=f"genre_{content_type}_{genre}")
    builder.button(text="⬅️ Назад", callback_data="to_main")
    builder.adjust(1)
    return builder.as_markup()

# --- ФУНКЦИИ ПОИСКА ---

async def search_tmdb(query):
    url = "https://api.themoviedb.org/3/search/multi"
    params = {
        "api_key": TMDB_API_KEY,
        "query": query,
        "language": "ru-RU"
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params)
            data = response.json()
            if data.get('results'):
                res = data['results'][0] # Берем первый результат
                m_type = res.get("media_type", "movie")
                name = res.get("title") or res.get("name")
                desc = res.get("overview", "Описание отсутствует.")
                img_path = res.get("poster_path")
                img_url = f"https://image.tmdb.org/t/p/w500{img_path}" if img_path else None
                
                return {
                    "name": name,
                    "desc": (desc[:400] + '...') if len(desc) > 400 else desc,
                    "img": img_url,
                    "link": f"https://www.themoviedb.org/{m_type}/{res.get('id')}",
                    "tag": f"🌐 Мировой поиск ({m_type})"
                }
        except Exception as e:
            print(f"Ошибка API: {e}")
    return None

# --- ХЕНДЛЕРЫ ---

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "✨ **Добро пожаловать!**\n\n"
        "1. Используй кнопки внизу для выбора из моего списка.\n"
        "2. Просто напиши название фильма, чтобы я нашел его во всем мире!", 
        reply_markup=get_reply_kb(),
        parse_mode="Markdown"
    )

# Обработка нажатий на Reply-кнопки (Фильм, Игра, Аниме)
@dp.message(F.text.in_(["🎬 Фильм", "🎮 Игра", "⛩ Аниме"]))
async def show_genres_menu(message: types.Message):
    mapping = {"🎬 Фильм": "movie", "🎮 Игра": "game", "⛩ Аниме": "anime"}
    content_type = mapping[message.text]
    await message.answer(f"Выбери жанр для категории {message.text}:", reply_markup=get_genres_kb(content_type))

# Обработка любого другого текста (Поиск)
@dp.message(F.text)
async def handle_text_search(message: types.Message):
    if message.text.startswith('/'): return # Игнорируем другие команды
    
    status_msg = await message.answer("🔍 Ищу в мировой базе...")
    item = await search_tmdb(message.text)
    await status_msg.delete()
    
    if item:
        caption = (f"🌟 **{item['name']}**\n\n"
                   f"📜 {item['desc']}\n\n"
                   f"🏷 {item['tag']}\n"
                   f"🔗 [Открыть подробнее]({item['link']})")
        if item['img']:
            await message.answer_photo(photo=item['img'], caption=caption, parse_mode="Markdown")
        else:
            await message.answer(caption, parse_mode="Markdown")
    else:
        await message.answer("❌ Ничего не нашлось. Попробуй ввести название точнее!")

# Обработка выбора жанра
@dp.callback_query(F.data.startswith("genre_"))
async def send_recommendation(callback: types.CallbackQuery):
    _, c_type, genre = callback.data.split("_")
    
    if c_type in DATA and genre in DATA[c_type]:
        item = random.choice(DATA[c_type][genre])
        caption = (f"🌟 **{item['name']}**\n\n"
                   f"📜 {item['desc']}\n\n"
                   f"🏷 {item['tag']}\n"
                   f"🔗 [Узнать больше]({item['link']})")
        try:
            await callback.message.answer_photo(photo=item['img'], caption=caption, parse_mode="Markdown")
        except:
            await callback.message.answer(caption, parse_mode="Markdown")
    
    await callback.answer()

@dp.callback_query(F.data == "to_main")
async def back_to_start(callback: types.CallbackQuery):
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer("Меню закрыто")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
