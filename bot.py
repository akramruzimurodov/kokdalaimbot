import asyncio
import logging
import os
import re
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message, 
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    ReplyKeyboardRemove
)
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# ==================== SOZLAMALAR ====================
BOT_TOKEN = "8725942855:AAFuJ2tNUc5y8in4UQM25zMC9Wg0HLlUnzk"  # O'zingizning Bot Tokeningizni yozing
ADMIN_ID = 1076674734  # O'zingizning Telegram ID-ingizni yozing (masalan: 123456789)
SHEET_NAME = "olimpaida_bot"  # Google Drive'dagi jadvalingiz nomi
CREDENTIALS_FILE = "credentials.json"
# ====================================================

# Logging
logging.basicConfig(level=logging.INFO)

# Google Sheets ulanish funksiyasi
def _get_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# FSM Holatlari
class OlympiadState(StatesGroup):
    full_name = State()
    grade = State()
    subject = State()
    phone = State()

dp = Dispatcher()

# Klaviaturalar
def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
        resize_keyboard=True
    )

def get_grade_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="8-sinf"), KeyboardButton(text="9-sinf")],
            [KeyboardButton(text="10-sinf"), KeyboardButton(text="11-sinf")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def get_subject_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="Matematika"), KeyboardButton(text="Fizika")],
            [KeyboardButton(text="Informatika"), KeyboardButton(text="Ingliz tili")],
            [KeyboardButton(text="Kimyo"), KeyboardButton(text="Biologiya")],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

def get_phone_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
            [KeyboardButton(text="❌ Bekor qilish")]
        ],
        resize_keyboard=True
    )

# Bekor qilish
@dp.message(F.text == "❌ Bekor qilish")
@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Hech qanday jarayon yo'q.", reply_markup=ReplyKeyboardRemove())
        return
    await state.clear()
    await message.answer("Ro'yxatdan o'tish bekor qilindi. Qayta boshlash uchun /start bosing.", reply_markup=ReplyKeyboardRemove())

# /start
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Assalomu alaykum, {message.from_user.full_name}!\n"
        "Maktabimiz olimpiadasiga ro'yxatdan o'tish botiga xush kelibsiz.\n\n"
        "Iltimos, Ism va Familiyangizni kiriting (Masalan: Aliyev Alisher):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OlympiadState.full_name)

# 1. Ism-familiya
@dp.message(OlympiadState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    name_text = message.text.strip()
    if len(name_text.split()) < 2:
        await message.answer(
            "Iltimos, ham Ism va ham Familiyangizni kiriting (Masalan: Aliyev Alisher):",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(full_name=name_text)
    await message.answer("Sinfingizni tanlang yoki yozib yuboring:", reply_markup=get_grade_keyboard())
    await state.set_state(OlympiadState.grade)

# 2. Sinf
@dp.message(OlympiadState.grade)
async def process_grade(message: Message, state: FSMContext):
    await state.update_data(grade=message.text.strip())
    await message.answer("Qaysi fan bo'yicha olimpiadada qatnashasiz? Fanni tanlang:", reply_markup=get_subject_keyboard())
    await state.set_state(OlympiadState.subject)

# 3. Fan
@dp.message(OlympiadState.subject)
async def process_subject(message: Message, state: FSMContext):
    await state.update_data(subject=message.text.strip())
    await message.answer(
        "Bog'lanish uchun telefon raqamingizni kiriting yoki pastdagi tugma orqali yuboring:",
        reply_markup=get_phone_keyboard()
    )
    await state.set_state(OlympiadState.phone)

# 4. Telefon (Kontakt)
@dp.message(OlympiadState.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext, bot: Bot):
    phone = message.contact.phone_number
    if not phone.startswith("+"):
        phone = "+" + phone
    await finish_registration(message, state, phone, bot)

# 4. Telefon (Matn)
@dp.message(OlympiadState.phone)
async def process_phone_text(message: Message, state: FSMContext, bot: Bot):
    phone = message.text.strip()
    if not re.match(r"^\+?[0-9]{9,15}$", phone):
        await message.answer(
            "Iltimos, to'g'ri telefon raqam kiriting (Masalan: +998901234567):",
            reply_markup=get_phone_keyboard()
        )
        return
    await finish_registration(message, state, phone, bot)

# Saqlash
async def finish_registration(message: Message, state: FSMContext, phone: str, bot: Bot):
    user_data = await state.get_data()
    full_name = user_data.get("full_name")
    grade = user_data.get("grade")
    subject = user_data.get("subject")
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    username_str = f"@{message.from_user.username}" if message.from_user.username else "Yo'q"

    loading_msg = await message.answer("Ma'lumotlaringiz saqlanmoqda, kuting...", reply_markup=ReplyKeyboardRemove())

    try:
        def save_to_sheet():
            scope = [
                "https://spreadsheets.google.com/feeds",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
            client = gspread.authorize(creds)
            sheet = client.open(SHEET_NAME).sheet1
            sheet.append_row([full_name, grade, subject, phone, current_time, username_str])

        await asyncio.to_thread(save_to_sheet)

    except Exception as e:
        logging.error(f"Google Sheets xatosi: {e}")
        await loading_msg.edit_text(f"❌ Xatolik yuz berdi: {str(e)}")
        await state.clear()
        return

    await loading_msg.edit_text(
        "Muvaffaqiyatli ro'yxatdan o'tdingiz!\n\n"
        f"Ism: {full_name}\n"
        f"Sinf: {grade}\n"
        f"Fan: {subject}\n"
        f"Tel: {phone}\n"
        f"Vaqt: {current_time}\n\n"
        "Olimpiadada omad tilaymiz!"
    )

    await state.clear()

# Render uchun web server
async def handle(request):
    return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.add_routes([web.get("/", handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    bot = Bot(token=BOT_TOKEN)
    await asyncio.gather(web_server(), dp.start_polling(bot))

if __name__ == "__main__":
    asyncio.run(main())
