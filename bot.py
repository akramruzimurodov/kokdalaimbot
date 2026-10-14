import asyncio
import logging
import re
from datetime import datetime
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

# Logging (Loglarni kuzatish uchun)
logging.basicConfig(level=logging.INFO)

# Google Sheets ulanish funksiyasi
def get_google_sheet():
    scope = [
        "https://spreadsheets.google.com/feeds",
        "https://www.googleapis.com/auth/drive"
    ]
    creds = ServiceAccountCredentials.from_json_keyfile_name(CREDENTIALS_FILE, scope)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

# FSM (Holatlar ketma-ketligi)
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

# Bekor qilish komandasi
@dp.message(F.text == "❌ Bekor qilish")
@dp.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("Xech qanday jarayon yo'q.", reply_markup=ReplyKeyboardRemove())
        return
    await state.clear()
    await message.answer("Ro'yxatdan o'tish bekor qilindi. Qayta boshlash uchun /start bosing.", reply_markup=ReplyKeyboardRemove())

# /start komandasi
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        f"Assalomu alaykum, **{message.from_user.full_name}**!\n"
        "Maktabimiz olimpiadasiga ro'yxatdan o'tish botiga xush kelibsiz.\n\n"
        "Iltimos, Ism va Familiyangizni kiriting (Masalan: *Aliyev Alisher*):",
        parse_mode="Markdown",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(OlympiadState.full_name)

# 1. Ism-familiya qabul qilish
@dp.message(OlympiadState.full_name)
async def process_full_name(message: Message, state: FSMContext):
    name_text = message.text.strip()
    if len(name_text.split()) < 2:
        await message.answer(
            "⚠️ Iltimos, ham **Ism** va ham **Familiya**ngizni kiriting (Masalan: Aliyev Alisher
