import asyncio
import json
import os
import random
import httpx
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
TOKEN = "8461545217:AAE-SfSolVZ6Mpx7aGDxQjJX_0JfxaHoXC8"
TMDB_API_KEY = "5e10d0f4cf73c8d9ef282c3d55690d07"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- ЗАГРУЗКА ЛОКАЛЬНОЙ БАЗЫ ---
def load_data():
    if os.path.exists('data.json'):
        with open('data.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"movie": {}, "game": {}, "anime": {}}

DATA = load_data()

# --- ГЛОБАЛЬНЫЙ ПОИСК (TMDB API) ---
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
                media_type = res.get("media_type", "movie")
                name = res.get("title") or res.get("name")
                desc = res.get("overview", "Описание временно отсутствует.")
                img_path = res.get("poster_path")
                img_url = f"https://image.tmdb.org/t/p/w500{img_path}" if img_path else None
                
                return {
                    "name": name,
                    "desc": (desc[:300] + '...') if len(desc) > 300 else desc,
                    "img": img_url,
                    "link": f"https://www.themoviedb.org/{media_type}/{res.get('id')}",
                    "tag": f"🌐 Мировой поиск ({media_type.capitalize()})"
                }
        except Exception as e:
            print(f"Ошибка поиска: {e}")
    return None

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def send_item(message, item):
    caption = (f"🌟 **{item['name']}**\n\n"
               f"📜 {item['desc']}\n\n"
               f"🏷 {item['tag']}\n"
               f"🔗 [Открыть подробнее]({item['link']})")
    try:
        if item.get('img'):
            await message.answer_photo(photo=item['img'], caption=caption, parse_mode="Markdown")
        else:
            await message.answer(caption, parse_mode="Markdown")
    except:
        await message.answer(caption, parse_mode="Markdown")

def search_local(query):
    query = query.lower()
    for cat in DATA.values():
        for genre_list in cat.values():
            for item in genre_list:
                if query in item['name'].lower():
                    return item
    return None

# --- ХЕНДЛЕРЫ ---
@dp.message(Command("start"))
async def start(message: types.Message):
    builder = InlineKeyboardBuilder()
    builder.button(text="🎬 Фильмы", callback_data="type_movie")
    builder.button(text="🎮 Игры", callback_доба="type_game")
    builder.button(text="⛩ Аниме", callback_data="type_anime")
    builder.button(text="🎲 Рандом", callback_data="random_all")
    builder.adjust(2, 1, 1)
    
    await message.answer("🍿 **Привет! Я твой медиа-гид.**\n\n"
                         "1. Используй кнопки для моих личных советов.\n"
                         "2. **Просто напиши название** любого фильма/сериала/аниме, и я найду его в мировой базе!", 
                         reply_markup=builder.as_markup(), parse_mode="Markdown")

@dp.message()
async def handle_search(message: types.Message):
    if not message.text: return
    
    # 1. Ищем в своих советах (data.json)
    local_item = search_local(message.text)
    if local_item:
        await message.answer("📌 Найдено в твоем списке:")
        await send_item(message, local_item)
        return

    # 2. Если не нашли, идем в TMDB
    msg = await message.answer("🔍 Ищу в мировой базе...")
    global_item = await search_tmdb(message.text)
    
    await msg.delete() # Удаляем надпись "ищу..."
    if global_item:
        await send_item(message, global_item)
    else:
        await message.answer("❌ Ничего не нашлось. Уточни название!")

# --- (Здесь должны быть остальные хендлеры кнопок из предыдущего кода) ---
# Добавь сюда функции callback_query для навигации по категориям и жанрам

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
