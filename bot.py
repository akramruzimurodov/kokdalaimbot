import asyncio
import logging
import os
import datetime
from aiogram import Bot, Dispatcher, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
import aiohttp
from aiohttp import web

TOKEN = "8725942855:AAFuJ2tNUc5y8in4UQM25zMC9Wg0HLlUnzk"

# 2-qadamda Google Apps Script'dan olgan Web App havolangizni shu yerga qo'ying:
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwnrv0OsJ5LjYt3-M8ANfZ0hmfymRlNXhUK4eUijGmaVdp7CUnvdIfbmAQCPupL5gZQ/exec"

# Bot va Dispatcher
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

class RegistrationStates(StatesGroup):
    full_name = State()
    grade = State()
    subject = State()
    phone = State()


@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.full_name)
    await message.answer(f"Assalomu alaykum, {html.bold(message.from_user.full_name)}!\n\nIsm va familiyangizni kiriting:")


@router.message(RegistrationStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(RegistrationStates.grade)
    await message.answer("Sinfingizni kiriting (masalan: 10-sinf):")


@router.message(RegistrationStates.grade)
async def process_grade(message: Message, state: FSMContext):
    await state.update_data(grade=message.text)
    await state.set_state(RegistrationStates.subject)
    await message.answer("Qaysi fandan ro'yxatdan o'tyapsiz? (fan nomini yozing):")


@router.message(RegistrationStates.subject)
async def process_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text)
    await state.set_state(RegistrationStates.phone)
    await message.answer("Telefon raqamingizni yuboring (masalan: +998901234567):")


@router.message(RegistrationStates.phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text
    user_data = await state.get_data()
    
    loading_msg = await message.answer("⏳ Ma'lumotlaringiz saqlanmoqda, kuting...")
    
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = str(message.from_user.id)
    
    payload = {
        "full_name": user_data.get('full_name'),
        "grade": user_data.get('grade'),
        "subject": user_data.get('subject'),
        "phone": phone,
        "time": now,
        "user_id": user_id
    }

    try:
        # Google Sheets'ga HTTP POST so'rov yuborish
        async with aiohttp.ClientSession() as session:
            async with session.post(WEB_APP_URL, json=payload) as response:
                if response.status == 200:
                    await loading_msg.delete()
                    await message.answer("✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!")
                else:
                    raise Exception(f"Server javobi: {response.status}")
                    
        await state.clear()
        
    except Exception as e:
        logging.error(f"Google Sheets xatosi: {e}")
        try:
            await loading_msg.delete()
        except:
            pass
        await message.answer("❌ Xatolik yuzaga keldi. Qaytadan urinib ko'ring.")
        await state.clear()


# Render Web Server (Keep-alive uchun)
async def handle_ping(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()


async def main():
    dp.include_router(router)
    await asyncio.gather(web_server(), dp.start_polling(bot))


If __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
