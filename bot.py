import asyncio
import logging
import os
import datetime
from aiogram import Bot, Dispatcher, Router, html, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
import aiohttp
from aiohttp import web

TOKEN = "8725942855:AAFuJ2tNUc5y8in4UQM25zMC9Wg0HLlUnzk"
WEB_APP_URL = "https://script.google.com/macros/s/AKfycbwnrv0OsJ5LjYt3-M8ANfZ0hmfymRlNXhUK4eUijGmaVdp7CUnvlfbmAQCPupL5gZQ/exec"

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()
router = Router()

class RegistrationStates(StatesGroup):
    full_name = State()
    grade = State()
    subject = State()
    phone = State()

# 1. Bekor qilish tugmasi
cancel_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="❌ Bekor qilish")]],
    resize_keyboard=True
)

# 2. Sinf tanlash tugmasi
grade_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="4-sinf")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)

# 3. Fan tanlash tugmalari (Matematika va Ingliz tili)
subject_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Matematika"), KeyboardButton(text="Ingliz tili")],
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)

# 4. Telefon raqam yuborish tugmasi
phone_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)],
        [KeyboardButton(text="❌ Bekor qilish")]
    ],
    resize_keyboard=True
)

@router.message(CommandStart())
async def command_start_handler(message: Message, state: FSMContext) -> None:
    await state.set_state(RegistrationStates.full_name)
    await message.answer(
        f"🎓 Assalomu alaykum, {html.bold(message.from_user.full_name)}!\n\n"
        f"<b>Ko'kdala tuman ixtisoslashtirilgan maktabi</b> olimpiadasiga ro'yxatdan o'tish botiga xush kelibsiz.\n\n"
        f"📝 Iltimos, o'quvchining <b>ism va familiyasini</b> kiriting (Masalan: <i>Alijon Valiyev</i>):",
        reply_markup=cancel_kb
    )

@router.message(F.text == "❌ Bekor qilish")
async def cancel_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "❌ <b>Ro'yxatdan o'tish bekor qilindi.</b>",
        reply_markup=ReplyKeyboardRemove()
    )
    await message.answer(
        "Qaytadan boshlash uchun /start buyrug'ini bosing."
    )

@router.message(RegistrationStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    await state.update_data(full_name=message.text)
    await state.set_state(RegistrationStates.grade)
    await message.answer(
        "🏫 Iltimos, o'quvchining <b>sinfini</b> tanlang:",
        reply_markup=grade_kb
    )

@router.message(RegistrationStates.grade)
async def process_grade(message: Message, state: FSMContext):
    if message.text != "4-sinf":
        await message.answer(
            "⚠️ Olimpiada faqat 4-sinflar uchun mo'ljallangan. Iltimos, quyidagi tugmani bosing:",
            reply_markup=grade_kb
        )
        return
        
    await state.update_data(grade=message.text)
    await state.set_state(RegistrationStates.subject)
    await message.answer(
        "📚 Qaysi fandan ro'yxatdan o'tyapsiz? Quyidagilardan birini tanlang:",
        reply_markup=subject_kb
    )

@router.message(RegistrationStates.subject)
async def process_subject(message: Message, state: FSMContext):
    if message.text not in ["Matematika", "Ingliz tili"]:
        await message.answer(
            "⚠️ Iltimos, faqat tugmalardan birini tanlang:",
            reply_markup=subject_kb
        )
        return
        
    await state.update_data(subject=message.text)
    await state.set_state(RegistrationStates.phone)
    await message.answer(
        "📞 Bog'lanish uchun <b>telefon raqamingizni</b> yuboring.\n\n"
        "Pastdagi <b>\"📱 Telefon raqamni yuborish\"</b> tugmasini bosing yoki qo'lda yozib yuboring (Masalan: <i>+998901234567</i>):",
        reply_markup=phone_kb
    )

@router.message(RegistrationStates.phone)
async def process_phone(message: Message, state: FSMContext):
    # Agar foydalanuvchi kontakt ulashish tugmasini bosgan bo'lsa
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = "+" + phone
    else:
        phone = message.text

    user_data = await state.get_data()
    
    loading_msg = await message.answer(
        "⏳ <b>Ma'lumotlaringiz saqlanmoqda, iltimos kuting...</b>",
        reply_markup=ReplyKeyboardRemove()
    )
    
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
        async with aiohttp.ClientSession() as session:
            async with session.post(WEB_APP_URL, json=payload) as response:
                if response.status == 200:
                    await loading_msg.delete()
                    await message.answer(
                        "✅ <b>Tabriklaymiz! Siz olimpiadaga muvaffaqiyatli ro'yxatdan o'tdingiz.</b>\n\n"
                        "Ma'lumotlaringiz bazaga muvaffaqiyatli saqlandi! 🎉",
                        reply_markup=ReplyKeyboardRemove()
                    )
                else:
                    raise Exception(f"Server javobi: {response.status}")
                    
        await state.clear()
        
    except Exception as e:
        logging.error(f"Google Sheets xatosi: {e}")
        try:
            await loading_msg.delete()
        except:
            pass
        await message.answer(
            "❌ <b>Xatolik yuzaga keldi. Qaytadan urinib ko'ring (/start).</b>",
            reply_markup=ReplyKeyboardRemove()
        )
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
