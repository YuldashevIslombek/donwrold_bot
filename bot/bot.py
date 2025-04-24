import asyncio
import os
from os import getenv
from uuid import uuid4  # Noyob identifikatorlar yaratish uchun

import requests
from aiogram import Bot, Dispatcher, html, F
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, BotCommand
from dotenv import load_dotenv

from utils import download_instagram

# Muhit o'zgaruvchilarini yuklash
load_dotenv()
# Bot tokenini muhit o'zgaruvchilaridan olish
TOKEN = getenv("BOT_TOKEN")

# Xabarlarni qayta ishlash uchun dispetcher
dp = Dispatcher()

# Media URL larini saqlash uchun lug'at
media_storage = {}

session = AiohttpSession(proxy="http://proxy.server:3128")

# Bot menyusiga buyruqlarni o'rnatish funksiyasi
async def set_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Botni ishga tushirish"),
        BotCommand(command="/help", description="Bot haqida yordam"),
    ]
    await bot.set_my_commands(commands)

# /start buyrug'i uchun ishlovchi
@dp.message(Command("start"))
async def command_start_handler(message: Message) -> None:
    # Salom xabarini yuborish
    await message.answer(
        f"Salom, {message.from_user.full_name}! 👋\n"
        "Bu bot Instagram Reel videolarini yuklab olishga yordam beradi.\n"
        "Instagram post havolasini yuboring, men uni yuklab olish uchun tugma yuboraman.\n"
        "Yordam uchun /help buyrug'ini ishlatish mumkin."
    )


# /help buyrug'i uchun ishlovchi
@dp.message(Command("help"))
async def command_help_handler(message: Message) -> None:
    # Yordam xabarini yuborish
    await message.answer(
        "📚 Bot yordami:\n"
        "1. Instagram Reel yoki post havolasini yuboring (masalan, https://www.instagram.com/...).\n"
        "2. 'Yuklab olish' tugmasini bosing, va men videoni yuboraman.\n"
        "3. Faqat ochiq postlar bilan ishlaydi.\n"
        "Savollar bo'lsa, yana /help buyrug'ini ishlatish mumkin!"
    )

# Instagram havolalari uchun ishlovchi
@dp.message(F.text.startswith(("https://www.instagram.com", "https://instagram.com")))
async def download_handler(message: Message):
    if message.text:
        # Instagramdan ma'lumotlarni API orqali olish
        result = download_instagram(link=message.text)
        if result.get("media"):
            url = result["media"][0].get("url")
            # Noyob identifikator yaratish
            media_id = str(uuid4())
            # URL ni lug'atda saqlash
            media_storage[media_id] = url
            # Yuklab olish uchun inline tugma yaratish
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Yuklab olish", callback_data=f"download_{media_id}")]
            ])
            # Tugma bilan xabar yuborish
            await message.answer("Mediani yuklab olish uchun tugmani bosing:", reply_markup=keyboard)
        else:
            # Media olishda xatolik bo'lsa xabar yuborish
            await message.answer("Mediaga ega bo‘lish imkonsiz. Havolani tekshiring.")


# Tugma bosilganda ishlovchi
@dp.callback_query(F.data.startswith("download_"))
async def process_download_callback(callback: CallbackQuery):
    # callback_data dan media identifikatorini olish
    media_id = callback.data.replace("download_", "")
    media_url = media_storage.get(media_id)

    if media_url:
        try:
            # Mediaga yuklab olish
            response = requests.get(media_url, stream=True)
            if response.status_code == 200:
                # Mediaga vaqtinchalik faylga saqlash
                temp_file = f"temp_{media_id}.mp4"
                with open(temp_file, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                # Mediaga FSInputFile sifatida yuborish
                media_file = FSInputFile(path=temp_file, filename=f"media_{media_id}.mp4")
                await callback.message.answer_video(video=media_file)
                # Vaqtinchalik faylni o'chirish
                os.remove(temp_file)
                # Yuborilganligini tasdiqlash
                await callback.answer("Media yuborildi!")
            else:
                # Yuklab olishda xatolik bo'lsa xabar yuborish
                await callback.message.answer("Mediaga yuklab olish imkonsiz. Boshqa havolani sinab ko‘ring.")
                await callback.answer()
            # Lug'atdan URL ni o'chirish
            del media_storage[media_id]
        except Exception as e:
            # Xatolik haqida xabar berish
            await callback.message.answer(f"Mediaga yuborishda xatolik: {str(e)}")
            await callback.answer()
    else:
        # Media topilmaganda xabar yuborish
        await callback.message.answer("Media topilmadi. Qayta urinib ko‘ring.")
        await callback.answer()


# Botni ishga tushirish
async def main() -> None:

    # Botni ishga tushirish
    bot = Bot(token=TOKEN, session=session)
    # Bot buyruqlarini o'rnatish
    await set_bot_commands(bot)
    # Xabarlarni qayta ishlashni boshlash
    await dp.start_polling(bot)


if __name__ == "__main__":
    print("Bot ishga tushmoqda...")
    asyncio.run(main())