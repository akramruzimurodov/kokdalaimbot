import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, Router, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
import gspread
from aiohttp import web
import datetime  # Vaqtni yozish uchun

TOKEN = "8725942855:AAFuJ2tNUc5y8in4UQM25zMC9Wg0HLlUnzk"  # O'z tokeningizni yozing

SHEET_NAME = "olimpaida_bot"   # Google Sheets jadvalingiz nomi

# gspread avtorizatsiyasi (credentials.json orqali)
gc = gspread.service_account(filename="credentials.json")

# Bot va Dispatcher
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

# Ro'yxatdan o'tish bosqichlari (FSM)
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


import datetime  # Vaqtni yozish uchun

@router.message(RegistrationStates.phone)
async def process_phone(message: Message, state: FSMContext):
    phone = message.text
    user_data = await state.get_data()
    
    loading_msg = await message.answer("⏳ Ma'lumotlaringiz saqlanmoqda, kuting...")
    
    # Hozirgi vaqtni olish
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    user_id = str(message.from_user.id)
    
    def save_to_sheet():
        sheet = gc.open(SHEET_NAME).sheet1
        # Jadvaldagi 6 ta ustunga moslab 6 ta qiymat yuboramiz:
        sheet.append_row([
            user_data.get('full_name'),
            user_data.get('grade'),
            user_data.get('subject'),
            phone,
            now,
            user_id
        ])

    try:
        await asyncio.to_thread(save_to_sheet)
        
        await loading_msg.delete()
        await message.answer("✅ Ro'yxatdan muvaffaqiyatli o'tdingiz!")
        await state.clear()
        
    except Exception as e:
        logging.error(f"Google Sheets xatosi: {e}")
        try:
            await loading_msg.delete()
        except:
            pass
        await message.answer(f"❌ Xatolik yuzaga keldi: {e}")
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
    # Veb server va bot polling'ni bir vaqtning o'zida ishga tushirish
    await asyncio.gather(web_server(), dp.start_polling(bot))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=open("/dev/null", "w") if False else None) # oddiy log
    asyncio.run(main())
    
