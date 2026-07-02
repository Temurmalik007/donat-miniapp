from aiogram import Router, F, Bot
from aiogram.types import (
    Message, CallbackQuery, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton,
)
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext

import database as db
from states import TopupFlow, AdminFlow
from config import ADMIN_IDS, CLICK_CARD, PAYME_CARD, CARD_OWNER, WEBAPP_URL

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def webapp_kb():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🛍 Do'konni ochish", web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True,
    )


def payment_method_kb():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💳 Click", callback_data="topup_pay:click")],
            [InlineKeyboardButton(text="💳 Payme", callback_data="topup_pay:payme")],
        ]
    )


def admin_topup_kb(topup_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"tadm_ok:{topup_id}"),
            InlineKeyboardButton(text="❌ Rad etish", callback_data=f"tadm_no:{topup_id}"),
        ]]
    )


def admin_order_kb(order_id):
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✔️ Bajarildi", callback_data=f"oadm_done:{order_id}"),
            InlineKeyboardButton(text="❌ Bekor qilish", callback_data=f"oadm_cancel:{order_id}"),
        ]]
    )


@router.message(CommandStart())
async def cmd_start(message: Message):
    db.upsert_user(message.from_user.id, message.from_user.username, message.from_user.full_name)
    await message.answer(
        "Assalomu alaykum! 👋\n\n"
        "O'yinlar uchun donat (UC, Olmos, Stars, Premium va h.k.) xarid qilish uchun "
        "do'konni oching 👇",
        reply_markup=webapp_kb(),
    )


# ---------- Hisobni to'ldirish (bot ichida, chunki chek-rasm yuborish kerak) ----------
@router.message(Command("topup"))
async def topup_start(message: Message, state: FSMContext):
    await message.answer("Necha so'mlik hisobni to'ldirmoqchisiz? Raqamda yozing (masalan: 50000):")
    await state.set_state(TopupFlow.waiting_amount)


@router.message(TopupFlow.waiting_amount)
async def topup_amount(message: Message, state: FSMContext):
    text = message.text.strip().replace(" ", "")
    if not text.isdigit() or int(text) < 1000:
        await message.answer("Iltimos, to'g'ri summa kiriting (kamida 1000 so'm).")
        return
    await state.update_data(amount=int(text))
    await message.answer("To'lov usulini tanlang:", reply_markup=payment_method_kb())
    await state.set_state(TopupFlow.waiting_method)


@router.callback_query(TopupFlow.waiting_method, F.data.startswith("topup_pay:"))
async def topup_method(callback: CallbackQuery, state: FSMContext):
    method = callback.data.split(":")[1]
    card = CLICK_CARD if method == "click" else PAYME_CARD
    data = await state.get_data()
    await callback.message.answer(
        f"<b>{data['amount']:,} so'm</b>ni quyidagi kartaga o'tkazing:\n".replace(",", " ") +
        f"💳 <code>{card}</code>\n👤 {CARD_OWNER}\n\n"
        "To'lov chekining (screenshot) rasmini shu yerga yuboring.",
        parse_mode="HTML",
    )
    await state.update_data(method=method)
    await state.set_state(TopupFlow.waiting_receipt)
    await callback.answer()


@router.message(TopupFlow.waiting_receipt, F.photo)
async def topup_receipt(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    topup_id = db.create_topup(message.from_user.id, data["amount"], data["method"], message.photo[-1].file_id)
    await message.answer(
        "Chek qabul qilindi ✅ Admin tekshiruvidan so'ng balansingiz to'ldiriladi.",
        reply_markup=webapp_kb(),
    )
    await state.clear()

    caption = (
        f"💰 <b>Hisob to'ldirish #{topup_id}</b>\n"
        f"Mijoz: {message.from_user.full_name} (@{message.from_user.username or '-'})\n"
        f"ID: <code>{message.from_user.id}</code>\n"
        f"Summa: {data['amount']:,} so'm\n".replace(",", " ") +
        f"Usul: {data['method'].upper()}"
    )
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_photo(admin_id, photo=message.photo[-1].file_id, caption=caption,
                                  parse_mode="HTML", reply_markup=admin_topup_kb(topup_id))
        except Exception:
            pass


@router.message(TopupFlow.waiting_receipt)
async def topup_receipt_wrong(message: Message):
    await message.answer("Iltimos, chekning rasmini (screenshot) yuboring 🖼")


# ---------- Admin: topup tasdiqlash ----------
@router.callback_query(F.data.startswith("tadm_ok:"))
async def topup_approve(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q", show_alert=True)
    topup_id = int(callback.data.split(":")[1])
    db.set_topup_status(topup_id, "tasdiqlandi")
    topup = db.get_topup(topup_id)
    await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n✅ TASDIQLANDI")
    await bot.send_message(topup["user_id"], f"✅ Balansingiz {topup['amount']:,} so'mga to'ldirildi!".replace(",", " "))
    await callback.answer("Tasdiqlandi")


@router.callback_query(F.data.startswith("tadm_no:"))
async def topup_reject(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q", show_alert=True)
    topup_id = int(callback.data.split(":")[1])
    db.set_topup_status(topup_id, "rad_etildi")
    topup = db.get_topup(topup_id)
    await callback.message.edit_caption(caption=(callback.message.caption or "") + "\n\n❌ RAD ETILDI")
    await bot.send_message(topup["user_id"], "❌ Hisobni to'ldirish so'rovingiz rad etildi. Admin bilan bog'laning.")
    await callback.answer("Rad etildi")


# ---------- Admin: buyurtmani bajarildi / bekor qilish ----------
@router.callback_query(F.data.startswith("oadm_done:"))
async def order_done(callback: CallbackQuery, bot: Bot):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q", show_alert=True)
    order_id = int(callback.data.split(":")[1])
    db.set_order_status(order_id, "bajarildi")
    order = db.get_order(order_id)
    await callback.message.edit_text((callback.message.text or callback.message.caption or "") + "\n\n🎉 BAJARILDI")
    await bot.send_message(order["user_id"], f"🎉 Buyurtmangiz #{order_id} yetkazib berildi!")
    await callback.answer("Bajarildi")


@router.callback_query(F.data.startswith("oadm_cancel:"))
async def order_cancel(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Ruxsat yo'q", show_alert=True)
    order_id = int(callback.data.split(":")[1])
    await state.update_data(cancel_order_id=order_id)
    await state.set_state(AdminFlow.waiting_reject_reason)
    await callback.message.answer(f"#{order_id} buyurtmani bekor qilish sababini yozing (pul balansga qaytariladi):")
    await callback.answer()


@router.message(AdminFlow.waiting_reject_reason)
async def order_cancel_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    order_id = data["cancel_order_id"]
    db.set_order_status(order_id, "bekor_qilindi", admin_comment=message.text.strip())
    order = db.get_order(order_id)
    await bot.send_message(
        order["user_id"],
        f"❌ Buyurtmangiz #{order_id} bekor qilindi.\nSabab: {message.text.strip()}\n"
        f"To'langan {order['price']:,} so'm balansingizga qaytarildi.".replace(",", " "),
    )
    await message.answer("Mijozga xabar berildi, pul balansiga qaytarildi.")
    await state.clear()


# ---------- Admin: katalog boshqarish ----------
@router.message(Command("admin"))
async def admin_panel(message: Message):
    if not is_admin(message.from_user.id):
        return
    await message.answer(
        "🛠 <b>Admin panel</b>\n\n"
        "/add_category — yangi kategoriya\n"
        "/add_product — yangi mahsulot\n",
        parse_mode="HTML",
    )


@router.message(Command("add_category"))
async def add_cat_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    await message.answer("Kategoriya nomini yuboring (masalan: PUBG MOBILE):")
    await state.set_state(AdminFlow.waiting_category_name)


@router.message(AdminFlow.waiting_category_name)
async def add_cat_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Emoji/ikonka yuboring (masalan: 🔫) yoki '-' deb yozing:")
    await state.set_state(AdminFlow.waiting_category_icon)


@router.message(AdminFlow.waiting_category_icon)
async def add_cat_icon(message: Message, state: FSMContext):
    icon = message.text.strip()
    await state.update_data(icon=("🎮" if icon == "-" else icon))
    await message.answer("Badge yozing (masalan: Global, AVTO, SNG) yoki '-' deb yozing:")
    await state.set_state(AdminFlow.waiting_category_badge)


@router.message(AdminFlow.waiting_category_badge)
async def add_cat_badge(message: Message, state: FSMContext):
    badge = message.text.strip()
    await state.update_data(badge=("" if badge == "-" else badge))
    await message.answer("Bu xizmat uchun o'yin ID (Player ID) so'ralsinmi? (ha / yo'q)")
    await state.set_state(AdminFlow.waiting_category_needs_id)


@router.message(AdminFlow.waiting_category_needs_id)
async def add_cat_needs_id(message: Message, state: FSMContext):
    needs_id = 1 if message.text.strip().lower() in ("ha", "yes", "+") else 0
    data = await state.get_data()
    cat_id = db.add_category(data["name"], data["icon"], data["badge"], needs_id)
    await message.answer(f"✅ Kategoriya qo'shildi: {data['name']} (ID: {cat_id})")
    await state.clear()


@router.message(Command("add_product"))
async def add_prod_start(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return
    categories = db.get_categories()
    if not categories:
        await message.answer("Avval /add_category orqali kategoriya qo'shing.")
        return
    lines = [f"{c['id']} — {c['name']}" for c in categories]
    await message.answer("Kategoriya ID sini yuboring:\n\n" + "\n".join(lines))
    await state.set_state(AdminFlow.waiting_product_category)


@router.message(AdminFlow.waiting_product_category)
async def add_prod_cat(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Faqat raqam yuboring.")
        return
    await state.update_data(category_id=int(message.text.strip()))
    await message.answer("Mahsulot nomi (masalan: 120 UC):")
    await state.set_state(AdminFlow.waiting_product_name)


@router.message(AdminFlow.waiting_product_name)
async def add_prod_name(message: Message, state: FSMContext):
    await state.update_data(name=message.text.strip())
    await message.answer("Narxi (so'mda, faqat raqam):")
    await state.set_state(AdminFlow.waiting_product_price)


@router.message(AdminFlow.waiting_product_price)
async def add_prod_price(message: Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("Faqat raqam yuboring.")
        return
    data = await state.get_data()
    db.add_product(data["category_id"], data["name"], int(message.text.strip()))
    await message.answer(f"✅ Mahsulot qo'shildi: {data['name']} — {int(message.text.strip()):,} so'm".replace(",", " "))
    await state.clear()
