# -*- coding: utf-8 -*-
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
 
# ─── ADMIN ───────────────────────────────────────────────────
def admin_main_kb():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Statistika"), KeyboardButton(text="🎬 Kino qo'shish")],
            [KeyboardButton(text="📋 Kinolar ro'yxati"), KeyboardButton(text="📢 E'lon berish")],
            [KeyboardButton(text="👥 Obuna statistikasi")],
        ],
        resize_keyboard=True
    )
 
# ─── USER ────────────────────────────────────────────────────
def user_main_kb(lang: str = "uz") -> ReplyKeyboardMarkup:
    texts = {
        "uz": [["💎 Premium", "👤 Profil"]],
        "ru": [["💎 Премиум", "👤 Профиль"]],
        "en": [["💎 Premium", "👤 Profile"]],
    }
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t) for t in row] for row in texts.get(lang, texts["uz"])],
        resize_keyboard=True
    )
 
# ─── TIL TANLASH ─────────────────────────────────────────────
def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇺🇿 O'zbek",  callback_data="lang:uz"),
            InlineKeyboardButton(text="🇷🇺 Русский",  callback_data="lang:ru"),
            InlineKeyboardButton(text="🇬🇧 English",  callback_data="lang:en"),
        ]
    ])
 
# ─── KANAL OBUNASI ────────────────────────────────────────────
def sub_channels_kb(channels: list, lang: str = "uz") -> InlineKeyboardMarkup:
    btn  = {"uz": "+ Obuna bo'lish",          "ru": "+ Podpisatsya",  "en": "+ Subscribe"}
    chk  = {"uz": "✅ A'zo bo'ldim, tekshir", "ru": "✅ Proverit",    "en": "✅ Check"}
    rows = [
        [InlineKeyboardButton(
            text=btn.get(lang, btn["uz"]),
            url=f"https://t.me/{ch.replace('@','')}"
        )]
        for ch in channels
    ]
    rows.append([InlineKeyboardButton(
        text=chk.get(lang, chk["uz"]),
        callback_data="check_channels"
    )])
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
# ─── VIP TAKLIF ───────────────────────────────────────────────
def vip_offer_kb(lang: str = "uz", admin_username: str = "") -> InlineKeyboardMarkup:
    buy  = {"uz": "💎 SOTIB OLISH",  "ru": "💎 КУПИТЬ",  "en": "💎 BUY NOW"}
    back = {"uz": "◀️ Orqaga",       "ru": "◀️ Назад",   "en": "◀️ Back"}
    rows = [
        [InlineKeyboardButton(text=buy.get(lang, buy["uz"]), callback_data="buy_premium")],
        [InlineKeyboardButton(text=back.get(lang, back["uz"]), callback_data="back_to_channels")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=rows)
 
# ─── TARIF TANLASH + ORQAGA ───────────────────────────────────
def tariff_back_kb(lang: str = "uz") -> InlineKeyboardMarkup:
    back = {"uz": "◀️ Orqaga", "ru": "◀️ Назад", "en": "◀️ Back"}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="1 oylik — 10 000 so'm",  callback_data="tariff:30:10000")],
        [InlineKeyboardButton(text="3 oylik — 25 000 so'm",  callback_data="tariff:90:25000")],
        [InlineKeyboardButton(text="1 yillik — 50 000 so'm", callback_data="tariff:365:50000")],
        [InlineKeyboardButton(text=back.get(lang, back["uz"]), callback_data="back_to_vip")],
    ])
 
# ─── TO'LOV SAHIFASI ──────────────────────────────────────────
def payment_kb(lang: str = "uz", admin_username: str = "") -> InlineKeyboardMarkup:
    paid = {"uz": "✅ To'lov qildim",  "ru": "✅ Я оплатил",  "en": "✅ I paid"}
    back = {"uz": "◀️ Orqaga",         "ru": "◀️ Назад",      "en": "◀️ Back"}
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=paid.get(lang, paid["uz"]),
            callback_data="i_paid"
        )],
        [InlineKeyboardButton(text=back.get(lang, back["uz"]), callback_data="back_to_tariffs")],
    ])
 
# ─── SAQLASH / BEKOR ──────────────────────────────────────────
def save_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Saqlash",       callback_data="save"),
        InlineKeyboardButton(text="❌ Bekor qilish",  callback_data="cancel"),
    ]])
 
# ─── ADMIN: CHEK TASDIQLASH ───────────────────────────────────
def payment_confirm_kb(payment_id: int, user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay_ok:{payment_id}:{user_id}"),
        InlineKeyboardButton(text="❌ Rad etish",  callback_data=f"pay_no:{payment_id}:{user_id}"),
    ]])
 
# ─── KINO O'CHIRISH ───────────────────────────────────────────
def movie_delete_kb(code: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"del_movie:{code}")
    ]])
 
# ─── E'LON TASDIQLASH ─────────────────────────────────────────
def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅ Yuborish", callback_data="broadcast_send"),
        InlineKeyboardButton(text="❌ Bekor",    callback_data="broadcast_cancel"),
    ]])
