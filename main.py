# -*- coding: utf-8 -*-
import asyncio
import datetime
import aiohttp
import tempfile
import os
import logging
from logging.handlers import RotatingFileHandler
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
 
from config import BOT_TOKEN, ADMINS, CHANNELS
from db import (
    init_db, upsert_movie, get_movie as db_get_movie,
    delete_movie, get_all_movies,
    log_usage, get_stats, get_total_users,
    save_user, get_subscription_stats, get_all_user_ids,
    set_user_lang, get_user_lang,
    set_premium, is_premium, get_premium_info,
    get_expiring_premium, get_premium_count,
    save_payment, get_payment, update_payment_status
)
from states import AddMovie, Premium, Broadcast
from keyboards import (
    admin_main_kb, user_main_kb, lang_kb,
    save_cancel_kb, payment_confirm_kb,
    movie_delete_kb, broadcast_confirm_kb,
    sub_channels_kb, vip_offer_kb,
    tariff_back_kb, payment_kb
)
 
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ✅ YANGI: Logging sozlamalari - xatolarni bot.log fayliga va konsolga yozadi
# RotatingFileHandler: fayl 5MB'dan oshsa, eski qismi avtomatik o'chiriladi (disk to'lib qolmaydi)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        RotatingFileHandler("bot.log", maxBytes=5 * 1024 * 1024, backupCount=2, encoding="utf-8"),
        logging.StreamHandler()
    ]
)

# ✅ YANGI: aiogram har bir update uchun "Update id=... is handled" deb yozadi -
# foydalanuvchi ko'paygach bu loglar juda ko'p bo'lib ketadi, shuning uchun o'chiramiz.
# Faqat xatoliklar (ERROR) ko'rsatiladi.
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
 
PHOTO_ID = "https://www.mldspot.com/storage/generated/June2021/movie-theater-audience.jpg"
ADMIN_USERNAME = "Alisher198711"
 
TARIFF_DAYS  = {"30": 30, "90": 90, "365": 365}
TARIFF_NAMES = {"30": "1 oylik", "90": "3 oylik", "365": "1 yillik"}
 
TEXTS = {
    "uz": {
        "welcome":          "👋 Salom {name}!\n\n🎬 Kerakli kino kodini kiriting.",
        "choose_lang":      "🌐 Tilni tanlang:",
        "lang_set":         "✅ Til o'rnatildi!",
        "must_subscribe":   "📢 Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:",
        "not_member":       "❌ Siz hali a'zo emassiz!",
        "not_found":        "❌ Bunday kod topilmadi.",
        "subscribe":        "⚠️ Botdan foydalanish uchun kanallarga a'zo bo'ling!",
        "vip_offer":        "💎 <b>Premium obuna nima uchun kerak?</b>\n\n✅ Kanallarga obuna bo'lish shart emas\n🚫 Reklamasiz\n🎬 Sifatli filmlar\n📞 24/7 qo'llab-quvvatlash xizmati",
        "premium_info":     "💎 <b>Premium obuna</b>\n\nPremium orqali:\n• Kanallarga obuna bo'lmasdan kino ko'rish\n• Reklamasiz foydalanish\n\n📋 Tarifni tanlang:",
        "payment_details":  "💳 <b>To'lov ma'lumotlari</b>\n\n🏦 Karta: <code>6262 5701 8285 9662</code>\n👤 Egasi: Siddiqov Alisher\n\n📦 Tarif: {tariff}\n💰 Narx: {price} so'm\n\n✅ To'lov qilgach chekni (rasm) yuboring.",
        "send_check":       "📸 To'lov chekini rasm sifatida yuboring:",
        "check_received":   "✅ Chekingiz qabul qilindi. Admin tekshirib tasdiqlaydi.",
        "premium_approved": "🎉 Premium faollashtirildi!\n⏰ Tarif: {tariff}\n📅 Tugash: {expires}",
        "premium_rejected": "❌ To'lovingiz rad etildi. To'g'ri chek yuboring.",
        "already_premium":  "✅ Sizda premium bor!\n📅 Tugash: {expires}",
        "profile":          "👤 <b>Profil</b>\n\n🆔 ID: <code>{user_id}</code>\n💎 Premium: {status}\n📅 Tugash: {expires}",
        "premium_expiring": "⚠️ Premium {days} kunda tugaydi! Yangilang.",
        "enter_code":       "🎬 Yoqtirgan filmingiz kodini kiriting:",
        "contact_admin":    "📞 Adminga bog'lanish",
    },
    "ru": {
        "welcome":          "👋 Привет {name}!\n\n🎬 Введите нужный код фильма.",
        "choose_lang":      "🌐 Выберите язык:",
        "lang_set":         "✅ Язык установлен!",
        "must_subscribe":   "📢 Чтобы пользоваться ботом, подпишитесь на каналы:",
        "not_member":       "❌ Вы ещё не подписаны!",
        "not_found":        "❌ Такой код не найден.",
        "subscribe":        "⚠️ Подпишитесь на каналы, чтобы использовать бота!",
        "vip_offer":        "💎 <b>Зачем нужна Premium подписка?</b>\n\n✅ Подписка на каналы не обязательна\n🚫 Без рекламы\n🎬 Фильмы в хорошем качестве\n📞 Поддержка 24/7",
        "premium_info":     "💎 <b>Premium подписка</b>\n\nС Premium:\n• Просмотр без подписки на каналы\n• Без рекламы\n\n📋 Выберите тариф:",
        "payment_details":  "💳 <b>Данные для оплаты</b>\n\n🏦 Карта: <code>6262 5701 8285 9662</code>\n👤 Владелец: Siddiqov Alisher\n\n📦 Тариф: {tariff}\n💰 Цена: {price} сум\n\n✅ После оплаты отправьте чек.",
        "send_check":       "📸 Отправьте чек оплаты как изображение:",
        "check_received":   "✅ Чек получен. Администратор проверит и подтвердит.",
        "premium_approved": "🎉 Premium активирован!\n⏰ Тариф: {tariff}\n📅 До: {expires}",
        "premium_rejected": "❌ Платёж отклонён. Отправьте правильный чек.",
        "already_premium":  "✅ У вас уже есть Premium!\n📅 До: {expires}",
        "profile":          "👤 <b>Профиль</b>\n\n🆔 ID: <code>{user_id}</code>\n💎 Premium: {status}\n📅 Истекает: {expires}",
        "premium_expiring": "⚠️ Premium истекает через {days} дней! Обновите.",
        "enter_code":       "🎬 Введите код понравившегося фильма:",
        "contact_admin":    "📞 Связаться с админом",
    },
    "en": {
        "welcome":          "👋 Hello {name}!\n\n🎬 Enter the required movie code.",
        "choose_lang":      "🌐 Choose your language:",
        "lang_set":         "✅ Language set!",
        "must_subscribe":   "📢 Please subscribe to the channels to use the bot:",
        "not_member":       "❌ You are not subscribed yet!",
        "not_found":        "❌ No movie found with this code.",
        "subscribe":        "⚠️ Please subscribe to the channels to use the bot!",
        "vip_offer":        "💎 <b>Why do you need Premium?</b>\n\n✅ No need to subscribe to channels\n🚫 Ad-free\n🎬 Quality films\n📞 24/7 support",
        "premium_info":     "💎 <b>Premium subscription</b>\n\nWith Premium:\n• Watch without subscribing to channels\n• Ad-free\n\n📋 Choose a plan:",
        "payment_details":  "💳 <b>Payment details</b>\n\n🏦 Card: <code>6262 5701 8285 9662</code>\n👤 Owner: Siddiqov Alisher\n\n📦 Plan: {tariff}\n💰 Price: {price} sum\n\n✅ Send the receipt after payment.",
        "send_check":       "📸 Send your payment receipt as an image:",
        "check_received":   "✅ Receipt received. Admin will confirm shortly.",
        "premium_approved": "🎉 Premium activated!\n⏰ Plan: {tariff}\n📅 Expires: {expires}",
        "premium_rejected": "❌ Payment rejected. Please send the correct receipt.",
        "already_premium":  "✅ You already have Premium!\n📅 Expires: {expires}",
        "profile":          "👤 <b>Profile</b>\n\n🆔 ID: <code>{user_id}</code>\n💎 Premium: {status}\n📅 Expires: {expires}",
        "premium_expiring": "⚠️ Premium expires in {days} days! Please renew.",
        "enter_code":       "🎬 Enter the code of your favorite movie:",
        "contact_admin":    "📞 Contact admin",
    },
}
 
ADMIN_BTNS = [
    "📊 Statistika", "🎬 Kino qo'shish",
    "👥 Obuna statistikasi", "📋 Kinolar ro'yxati", "📢 E'lon berish",
    "📦 Yuklangan kinolar"
]
USER_BTNS = ["💎 Premium", "💎 Премиум", "👤 Profil", "👤 Профиль", "👤 Profile"]
 
def t(lang, key, **kwargs):
    text = TEXTS.get(lang, TEXTS["uz"]).get(key, key)
    return text.format(**kwargs) if kwargs else text
 
def is_admin(user_id):
    return user_id in ADMINS
 
async def check_subscription(user_id):
    try:
        for ch in CHANNELS:
            m = await bot.get_chat_member(ch, user_id)
            if m.status not in ["member", "administrator", "creator"]:
                return False
        return True
    except Exception:
        return False
 
async def get_unsubscribed_channels(user_id):
    unsubbed = []
    for ch in CHANNELS:
        try:
            m = await bot.get_chat_member(ch, user_id)
            if m.status not in ["member", "administrator", "creator"]:
                unsubbed.append(ch)
        except Exception:
            unsubbed.append(ch)
    return unsubbed
 
# ✅ TUZATILDI: foto xabarga edit_text ishlamaydi
async def show_vip_offer(target, lang, name=None):
    text = t(lang, "vip_offer")
    kb = vip_offer_kb(lang, ADMIN_USERNAME)
    if isinstance(target, CallbackQuery):
        try:
            await target.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception:
            try:
                await target.message.edit_caption(caption=text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                await bot.send_message(target.from_user.id, text, reply_markup=kb, parse_mode="HTML")
        await target.answer()
    else:
        await target.answer(text, reply_markup=kb, parse_mode="HTML")
 
# ✅ YANGI: URL dan video yuklab Telegramga joylash
async def download_and_upload_video(message: Message, url: str):
    status_msg = await message.answer("⏳ Video yuklanmoqda, kuting...")
    tmp_path = None
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=300)) as resp:
                if resp.status != 200:
                    await status_msg.edit_text(f"❌ Yuklab bo'lmadi. Server javobi: {resp.status}")
                    return
                content_type = resp.headers.get("Content-Type", "")
                if "video" not in content_type and not url.lower().endswith((".mp4", ".mkv", ".avi", ".mov")):
                    await status_msg.edit_text("❌ Bu havola video fayl emas.")
                    return
                with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
                    tmp_path = tmp.name
                    downloaded = 0
                    async for chunk in resp.content.iter_chunked(1024 * 1024):
                        tmp.write(chunk)
                        downloaded += len(chunk)
 
        await status_msg.edit_text(
            f"✅ Yuklandi ({downloaded // 1024 // 1024} MB)\n⏳ Telegramga jo'natilmoqda..."
        )
        video_file = FSInputFile(tmp_path, filename="video.mp4")
        sent = await message.answer_video(
            video=video_file,
            caption="📎 URL dan yuklandi. Endi /add orqali bazaga qo'shing."
        )
        await status_msg.edit_text(
            f"✅ Video Telegramga yuklandi!\n\n"
            f"📋 <b>file_id:</b>\n<code>{sent.video.file_id}</code>\n\n"
            f"Endi /add bosib, shu videoni forward qiling yoki file_id ni nusxalab ishlating.",
            parse_mode="HTML"
        )
    except asyncio.TimeoutError:
        await status_msg.edit_text("❌ Vaqt tugadi. Video juda katta yoki server sekin.")
    except Exception as e:
        await status_msg.edit_text(f"❌ Xato: {str(e)[:200]}")
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
 
@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    await save_user(message.from_user.id)
    if PHOTO_ID:
        await message.answer_photo(
            photo=PHOTO_ID,
            caption=t("uz", "choose_lang"),
            reply_markup=lang_kb()
        )
    else:
        await message.answer(t("uz", "choose_lang"), reply_markup=lang_kb())
 
@dp.callback_query(F.data.startswith("lang:"))
async def set_lang(call: CallbackQuery, state: FSMContext):
    lang = call.data.split(":")[1]
    user_id = call.from_user.id
    await set_user_lang(user_id, lang)
    name = call.from_user.first_name
    await call.message.edit_caption(caption=t(lang, "welcome", name=name))
    await call.answer(t(lang, "lang_set"))
    if is_admin(user_id):
        await bot.send_message(user_id, t(lang, "enter_code"), reply_markup=admin_main_kb())
        return
    kb = user_main_kb(lang)
    await bot.send_message(user_id, t(lang, "enter_code"), reply_markup=kb)
    if not await check_subscription(user_id):
        await bot.send_message(
            user_id,
            t(lang, "must_subscribe"),
            reply_markup=sub_channels_kb(CHANNELS, lang)
        )
 
@dp.callback_query(F.data == "check_channels")
async def check_channels_cb(call: CallbackQuery):
    user_id = call.from_user.id
    lang = await get_user_lang(user_id)
    unsubbed = await get_unsubscribed_channels(user_id)
    if unsubbed:
        await call.answer(t(lang, "not_member"), show_alert=True)
        await call.message.edit_text(
            t(lang, "must_subscribe"),
            reply_markup=sub_channels_kb(unsubbed, lang)
        )
        return
    await call.answer()
    name = call.from_user.first_name
    await call.message.edit_text(t(lang, "welcome", name=name))
 
@dp.message(F.photo)
async def photo_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()
    if current_state == Broadcast.waiting_content.state:
        await state.update_data(
            content_type="photo",
            file_id=message.photo[-1].file_id,
            caption=message.caption or ""
        )
        await state.set_state(Broadcast.confirm)
        await message.answer(
            "👆 Bu rasm barcha foydalanuvchilarga yuboriladi.\n\nDavom etamizmi?",
            reply_markup=broadcast_confirm_kb()
        )
        return
    if current_state == Premium.sending_check.state:
        lang = await get_user_lang(user_id)
        data = await state.get_data()
        tariff_key = data.get("tariff_key", "30")
        days = data.get("days", 30)
        photo_file_id = message.photo[-1].file_id
        payment_id = await save_payment(user_id, photo_file_id, tariff_key)
        tariff_name = TARIFF_NAMES.get(tariff_key, tariff_key)
        for admin_id in ADMINS:
            try:
                await bot.send_photo(
                    chat_id=admin_id,
                    photo=photo_file_id,
                    caption=(
                        f"💳 <b>Yangi to'lov so'rovi</b>\n\n"
                        f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                        f"🆔 ID: <code>{user_id}</code>\n"
                        f"📦 Tarif: {tariff_name} ({days} kun)\n"
                        f"🕐 Vaqt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    ),
                    reply_markup=payment_confirm_kb(payment_id, user_id),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await state.clear()
        await message.answer(t(lang, "check_received"))
        return
    if is_admin(user_id):
        await message.answer(f"`{message.photo[-1].file_id}`")
 
@dp.message(F.document)
async def document_handler(message: Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()
    if current_state == Broadcast.waiting_content.state:
        await state.update_data(
            content_type="document",
            file_id=message.document.file_id,
            caption=message.caption or ""
        )
        await state.set_state(Broadcast.confirm)
        await message.answer(
            "👆 Bu fayl barcha foydalanuvchilarga yuboriladi.\n\nDavom etamizmi?",
            reply_markup=broadcast_confirm_kb()
        )
        return
    if current_state == Premium.sending_check.state:
        lang = await get_user_lang(user_id)
        data = await state.get_data()
        tariff_key = data.get("tariff_key", "30")
        days = data.get("days", 30)
        doc_file_id = message.document.file_id
        payment_id = await save_payment(user_id, doc_file_id, tariff_key)
        tariff_name = TARIFF_NAMES.get(tariff_key, tariff_key)
        for admin_id in ADMINS:
            try:
                await bot.send_document(
                    chat_id=admin_id,
                    document=doc_file_id,
                    caption=(
                        f"💳 <b>Yangi to'lov so'rovi (fayl)</b>\n\n"
                        f"👤 Foydalanuvchi: <a href='tg://user?id={user_id}'>{message.from_user.first_name}</a>\n"
                        f"🆔 ID: <code>{user_id}</code>\n"
                        f"📦 Tarif: {tariff_name} ({days} kun)\n"
                        f"🕐 Vaqt: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}"
                    ),
                    reply_markup=payment_confirm_kb(payment_id, user_id),
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await state.clear()
        await message.answer(t(lang, "check_received"))
        return
    if is_admin(user_id):
        await message.answer(f"`{message.document.file_id}`")
 
async def send_stats(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await get_stats()
    total_users = await get_total_users()
    premium_cnt = await get_premium_count()
    text = "📊 <b>Statistika</b>\n"
    text += f"👥 Jami foydalanuvchilar: <b>{total_users}</b>\n"
    text += f"💎 Aktiv premium: <b>{premium_cnt}</b>\n\n"
    if rows:
        text += "🎬 <b>Eng ko'p so'ralgan kinolar:</b>\n"
        for i, (code, cnt) in enumerate(rows, 1):
            text += f"{i}. Kod <code>{code}</code> — <b>{cnt}</b> marta\n"
    else:
        text += "Hali kino so'ralmagan."
    await message.answer(text, parse_mode="HTML")
 
@dp.message(F.text == "📊 Statistika")
async def stats_btn(message: Message):
    await send_stats(message)
 
@dp.message(Command("stat"))
async def stats_cmd(message: Message):
    await send_stats(message)
 
@dp.message(F.text == "👥 Obuna statistikasi")
async def subscription_stats_btn(message: Message):
    if not is_admin(message.from_user.id):
        return
    total_db = await get_subscription_stats()
    active_counts = {}
    for ch in CHANNELS:
        try:
            count = await bot.get_chat_member_count(ch)
            active_counts[ch] = count
        except Exception:
            active_counts[ch] = "—"
    text = "👥 <b>Obuna statistikasi</b>\n\n"
    text += f"📥 Botga /start bosgan jami: <b>{total_db}</b>\n\n"
    text += "📢 <b>Kanallar obunachilar soni:</b>\n"
    for ch, cnt in active_counts.items():
        text += f"• {ch} — <b>{cnt}</b> ta\n"
    await message.answer(text, parse_mode="HTML")
 
async def start_add(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(AddMovie.code)
    await message.answer("🎬 Kino kodini kiriting (masalan: 101):")
 
@dp.message(F.text == "🎬 Kino qo'shish")
async def add_btn(message: Message, state: FSMContext):
    await start_add(message, state)
 
@dp.message(Command("add"))
async def add_cmd(message: Message, state: FSMContext):
    await start_add(message, state)
 
@dp.message(AddMovie.code, F.text)
async def add_code(message: Message, state: FSMContext):
    code = message.text.strip()
    if len(code) > 30:
        await message.answer("❌ Kod juda uzun.")
        return
    await state.update_data(code=code)
    await state.set_state(AddMovie.caption)
    await message.answer("✍️ Caption kiriting (yoki — yozing):")
 
@dp.message(AddMovie.caption, F.text)
async def add_caption(message: Message, state: FSMContext):
    await state.update_data(caption=message.text.strip())
    await state.set_state(AddMovie.video)
    await message.answer("🎬 Endi videoni yuboring.")
 
@dp.message(AddMovie.video, F.video)
async def add_video(message: Message, state: FSMContext):
    await state.update_data(file_id=message.video.file_id)
    data = await state.get_data()
    await state.set_state(AddMovie.confirm)
    await message.answer(
        f"📌 Tekshirish:\n🎬 Kod: {data['code']}\n✍️ Caption: {data.get('caption','')}\n\nSaqlaymizmi?",
        reply_markup=save_cancel_kb()
    )
 
@dp.message(AddMovie.video)
async def add_video_wrong(message: Message):
    await message.answer("❌ Faqat video yuboring.")
 
@dp.callback_query(F.data == "cancel")
async def cancel_add(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ Bekor qilindi.")
    await call.answer()
 
# ✅ TUZATILDI: state yo'qolgan bo'lsa xato chiqmaydi
@dp.callback_query(F.data == "save")
async def save_add(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    if "code" not in data or "file_id" not in data:
        await state.clear()
        await call.message.edit_text("❌ Xato: ma'lumot yo'qoldi. Qaytadan boshlang /add")
        await call.answer()
        return
    await upsert_movie(code=data["code"], caption=data.get("caption", ""), file_id=data["file_id"])
    await state.clear()
    await call.message.edit_text("✅ Saqlandi!")
    await call.answer()
 
@dp.message(F.text == "📋 Kinolar ro'yxati")
async def movies_list(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await get_all_movies()
    if not rows:
        await message.answer("🎬 Hali kino yo'q.")
        return
    for code, caption, created_at in rows:
        name = caption if caption and caption != "—" else "(caption yo'q)"
        await message.answer(
            f"🎬 Kod: <code>{code}</code>\n📝 {name}",
            reply_markup=movie_delete_kb(code),
            parse_mode="HTML"
        )
 
@dp.callback_query(F.data.startswith("del_movie:"))
async def delete_movie_cb(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    code = call.data.split(":")[1]
    await delete_movie(code)
    await call.message.edit_text(f"🗑 Kod <code>{code}</code> o'chirildi.", parse_mode="HTML")
    await call.answer("O'chirildi!")
 
# ✅ YANGI: Yuklangan kinolarning umumiy ro'yxati (tartib raqami + kod + yuklangan vaqt)
@dp.message(F.text == "📦 Yuklangan kinolar")
async def uploaded_movies_summary(message: Message):
    if not is_admin(message.from_user.id):
        return
    rows = await get_all_movies()
    if not rows:
        await message.answer("🎬 Hali kino yo'q.")
        return
 
    header = f"🎬 <b>Yuklangan kinolar:</b> {len(rows)} ta\n\n"
    lines = []
    for i, (code, caption, created_at) in enumerate(rows, 1):
        when = "—"
        if created_at:
            # ✅ TUZATILDI: bazadagi vaqt UTC bo'yicha saqlanadi, O'zbekiston vaqtiga (+5) o'tkazamiz
            try:
                dt_obj = datetime.datetime.strptime(created_at, "%Y-%m-%d %H:%M:%S")
                dt_obj += datetime.timedelta(hours=5)
                when = dt_obj.strftime("%Y-%m-%d %H:%M")
            except (ValueError, TypeError):
                when = created_at
        lines.append(f"{i} - kod {code} | {when}")
 
    # Telegram xabar limiti ~4096 belgi, shu sababli bo'lib yuboramiz
    chunk = header
    for line in lines:
        if len(chunk) + len(line) + 1 > 4000:
            await message.answer(chunk, parse_mode="HTML")
            chunk = ""
        chunk += line + "\n"
    if chunk.strip():
        await message.answer(chunk, parse_mode="HTML")
 
@dp.message(F.text == "📢 E'lon berish")
async def broadcast_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await state.clear()
    await state.set_state(Broadcast.waiting_content)
    await message.answer(
        "📢 E'lon mazmunini yuboring.\nMatn, rasm yoki video yuborishingiz mumkin."
    )
 
@dp.message(Broadcast.waiting_content, F.video)
async def broadcast_video(message: Message, state: FSMContext):
    await state.update_data(content_type="video", file_id=message.video.file_id, caption=message.caption or "")
    await state.set_state(Broadcast.confirm)
    await message.answer("👆 Bu video barcha foydalanuvchilarga yuboriladi.\n\nDavom etamizmi?", reply_markup=broadcast_confirm_kb())
 
@dp.message(Broadcast.waiting_content, F.text)
async def broadcast_text(message: Message, state: FSMContext):
    await state.update_data(content_type="text", text=message.text)
    await state.set_state(Broadcast.confirm)
    await message.answer("👆 Bu matn barcha foydalanuvchilarga yuboriladi.\n\nDavom etamizmi?", reply_markup=broadcast_confirm_kb())
 
@dp.callback_query(F.data == "broadcast_cancel")
async def broadcast_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("❌ E'lon bekor qilindi.")
    await call.answer()
 
@dp.callback_query(F.data == "broadcast_send")
async def broadcast_send(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    await call.message.edit_text("📤 Yuborilmoqda...")
    await call.answer()
    user_ids = await get_all_user_ids()
    sent = failed = 0
    for uid in user_ids:
        try:
            ct = data["content_type"]
            if ct == "text":
                await bot.send_message(uid, data["text"])
            elif ct == "photo":
                await bot.send_photo(uid, data["file_id"], caption=data.get("caption",""))
            elif ct == "video":
                await bot.send_video(uid, data["file_id"], caption=data.get("caption",""))
            sent += 1
            await asyncio.sleep(0.05)
        except Exception:
            failed += 1
    await bot.send_message(
        call.from_user.id,
        f"✅ E'lon yuborildi!\n\n📨 Yuborildi: <b>{sent}</b> ta\n❌ Yetmadi: <b>{failed}</b> ta",
        parse_mode="HTML"
    )
 
@dp.callback_query(F.data.startswith("pay_ok:"))
async def payment_approve(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    _, payment_id, user_id = call.data.split(":")
    payment_id, user_id = int(payment_id), int(user_id)
    payment = await get_payment(payment_id)
    if not payment:
        await call.answer("To'lov topilmadi!", show_alert=True)
        return
    tariff_key = payment[3]
    days = TARIFF_DAYS.get(tariff_key, 30)
    tariff_name = TARIFF_NAMES.get(tariff_key, "1 oylik")
    await set_premium(user_id, days)
    await update_payment_status(payment_id, "approved")
    lang = await get_user_lang(user_id)
    info = await get_premium_info(user_id)
    expires = info[0] if info else "—"
    try:
        await bot.send_message(user_id, t(lang, "premium_approved", tariff=tariff_name, expires=expires), parse_mode="HTML")
    except Exception:
        pass
    try:
        await call.message.edit_caption(
            caption=call.message.caption + f"\n\n✅ <b>TASDIQLANDI</b> — {call.from_user.first_name}",
            parse_mode="HTML"
        )
    except Exception:
        await call.message.edit_text(
            (call.message.caption or call.message.text or "") + f"\n\n✅ <b>TASDIQLANDI</b> — {call.from_user.first_name}",
            parse_mode="HTML"
        )
    await call.answer("✅ Premium berildi!")
 
@dp.callback_query(F.data.startswith("pay_no:"))
async def payment_reject(call: CallbackQuery):
    if not is_admin(call.from_user.id):
        return
    _, payment_id, user_id = call.data.split(":")
    payment_id, user_id = int(payment_id), int(user_id)
    await update_payment_status(payment_id, "rejected")
    lang = await get_user_lang(user_id)
    # ✅ YANGI: to'lov rad etilganda, foydalanuvchi adminga bog'lanishi uchun tugma
    contact_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "contact_admin"), url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    try:
        await bot.send_message(user_id, t(lang, "premium_rejected"), reply_markup=contact_kb)
    except Exception:
        pass
    try:
        await call.message.edit_caption(
            caption=call.message.caption + f"\n\n❌ <b>RAD ETILDI</b> — {call.from_user.first_name}",
            parse_mode="HTML"
        )
    except Exception:
        await call.message.edit_text(
            (call.message.caption or call.message.text or "") + f"\n\n❌ <b>RAD ETILDI</b> — {call.from_user.first_name}",
            parse_mode="HTML"
        )
    await call.answer("❌ Rad etildi!")
 
@dp.callback_query(F.data == "buy_premium")
async def buy_premium_cb(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    lang = await get_user_lang(user_id)
    if await is_premium(user_id):
        info = await get_premium_info(user_id)
        expires = info[0] if info else "—"
        await call.answer()
        await call.message.edit_text(t(lang, "already_premium", expires=expires), parse_mode="HTML")
        return
    await state.set_state(Premium.choosing_tariff)
    await call.message.edit_text(
        t(lang, "premium_info"),
        reply_markup=tariff_back_kb(lang),
        parse_mode="HTML"
    )
    await call.answer()
 
@dp.callback_query(F.data.startswith("tariff:"))
async def choose_tariff(call: CallbackQuery, state: FSMContext):
    _, days, price = call.data.split(":")
    lang = await get_user_lang(call.from_user.id)
    await state.update_data(tariff_key=days, days=int(days))
    await state.set_state(Premium.sending_check)
    tariff_name = TARIFF_NAMES.get(days, days)
    await call.message.edit_text(
        t(lang, "payment_details", tariff=tariff_name, price=price),
        reply_markup=payment_kb(lang, ADMIN_USERNAME),
        parse_mode="HTML"
    )
    await call.answer()
 
@dp.callback_query(F.data == "i_paid")
async def i_paid_cb(call: CallbackQuery, state: FSMContext):
    user_id = call.from_user.id
    lang = await get_user_lang(user_id)
    await state.set_state(Premium.sending_check)
    await call.message.edit_text(t(lang, "send_check"))
    await call.answer()
 
@dp.callback_query(F.data == "back_to_channels")
async def back_to_channels(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(call.from_user.id)
    await call.message.edit_text(
        t(lang, "must_subscribe"),
        reply_markup=sub_channels_kb(CHANNELS, lang)
    )
    await call.answer()
 
@dp.callback_query(F.data == "back_to_vip")
async def back_to_vip(call: CallbackQuery, state: FSMContext):
    await state.clear()
    lang = await get_user_lang(call.from_user.id)
    await call.message.edit_text(
        t(lang, "vip_offer"),
        reply_markup=vip_offer_kb(lang, ADMIN_USERNAME),
        parse_mode="HTML"
    )
    await call.answer()
 
@dp.callback_query(F.data == "back_to_tariffs")
async def back_to_tariffs(call: CallbackQuery, state: FSMContext):
    lang = await get_user_lang(call.from_user.id)
    await state.set_state(Premium.choosing_tariff)
    await call.message.edit_text(
        t(lang, "premium_info"),
        reply_markup=tariff_back_kb(lang),
        parse_mode="HTML"
    )
    await call.answer()
 
@dp.message(F.text.in_(["💎 Premium", "💎 Премиум"]))
async def premium_menu(message: Message, state: FSMContext):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    if await is_premium(user_id):
        info = await get_premium_info(user_id)
        expires = info[0] if info else "—"
        await message.answer(t(lang, "already_premium", expires=expires), parse_mode="HTML")
        return
    await state.set_state(Premium.choosing_tariff)
    await message.answer(t(lang, "premium_info"), reply_markup=tariff_back_kb(lang), parse_mode="HTML")
 
@dp.message(F.text.in_(["👤 Profil", "👤 Профиль", "👤 Profile"]))
async def profile_menu(message: Message):
    user_id = message.from_user.id
    lang = await get_user_lang(user_id)
    prem = await is_premium(user_id)
    info = await get_premium_info(user_id)
    expires = info[0] if info else "—"
    status_map = {"uz": ("✅ Aktiv","❌ Yo'q"), "ru": ("✅ Активно","❌ Нет"), "en": ("✅ Active","❌ None")}
    yes, no = status_map.get(lang, status_map["uz"])
    await message.answer(
        t(lang, "profile", user_id=user_id, status=yes if prem else no, expires=expires if prem else "—"),
        parse_mode="HTML"
    )
 
# ✅ YANGI: Admin http:// havola yuborganda video yuklab oladi
@dp.message(F.text & F.text.startswith("http"))
async def handle_url(message: Message):
    if not is_admin(message.from_user.id):
        return
    url = message.text.strip()
    if any(url.lower().endswith(ext) for ext in (".mp4", ".mkv", ".avi", ".mov")):
        await download_and_upload_video(message, url)
    else:
        await message.answer(
            "⚠️ Faqat to'g'ridan-to'g'ri video havolalar ishlaydi.\n\n"
            "Masalan: <code>https://fayllar1.ru/video.mp4</code>",
            parse_mode="HTML"
        )
 
@dp.message(F.text & ~F.text.startswith("/"))
async def user_get_movie(message: Message):
    user_id = message.from_user.id
    code = message.text.strip()
    if code in ADMIN_BTNS or code in USER_BTNS:
        return
    lang = await get_user_lang(user_id)
    if not await is_premium(user_id):
        if not await check_subscription(user_id):
            await message.answer(
                t(lang, "subscribe"),
                reply_markup=sub_channels_kb(CHANNELS, lang)
            )
            return
    row = await db_get_movie(code)
    if not row:
        await message.answer(t(lang, "not_found"))
        return
    _, caption, file_id = row
    await log_usage(user_id, code)
    await message.answer_video(video=file_id, caption=caption or "", protect_content=True)
 
@dp.callback_query(F.data.startswith("check_sub:"))
async def check_sub_callback(call: CallbackQuery):
    user_id = call.from_user.id
    code = call.data.split(":")[1]
    lang = await get_user_lang(user_id)
    if not await check_subscription(user_id):
        await call.answer(t(lang, "not_member"), show_alert=True)
        return
    row = await db_get_movie(code)
    if not row:
        await call.message.edit_text(t(lang, "not_found"))
        return
    _, caption, file_id = row
    await log_usage(user_id, code)
    await call.message.delete()
    await bot.send_video(chat_id=user_id, video=file_id, caption=caption or "", protect_content=True)
    await call.answer()
 
async def check_expiring_premiums():
    while True:
        await asyncio.sleep(86400)
        rows = await get_expiring_premium(days=3)
        for user_id, expires_at in rows:
            lang = await get_user_lang(user_id)
            try:
                await bot.send_message(user_id, t(lang, "premium_expiring", days=3))
            except Exception:
                pass
 
async def main():
    await init_db()
    asyncio.create_task(check_expiring_premiums())
    logging.info("Bot ishga tushdi")

    # ✅ YANGI: Agar polling biror sababdan to'xtab qolsa, bot avtomatik qayta ishga tushadi
    while True:
        try:
            await dp.start_polling(bot)
        except Exception as e:
            logging.error(f"Bot xato bilan to'xtadi: {e}")
            await asyncio.sleep(5)
            logging.info("Bot qayta ishga tushyapti...")

 
if __name__ == "__main__":
    asyncio.run(main())
