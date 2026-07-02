import asyncio
import contextlib
import logging
import secrets

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
from config import BOT_TOKEN, PORT, ADMIN_PANEL_USERNAME, ADMIN_PANEL_PASSWORD
from webapp_auth import validate_init_data
import bot_handlers

logging.basicConfig(level=logging.INFO)

db.init_db()

bot = Bot(token=BOT_TOKEN) if BOT_TOKEN else None
dp = Dispatcher(storage=MemoryStorage())
dp.include_router(bot_handlers.router)

app = FastAPI()
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

_polling_task = None


@app.on_event("startup")
async def on_startup():
    global _polling_task
    if bot:
        await bot.delete_webhook(drop_pending_updates=True)
        _polling_task = asyncio.create_task(dp.start_polling(bot))


@app.on_event("shutdown")
async def on_shutdown():
    if _polling_task:
        _polling_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await _polling_task


# ---------------- Auth helper (mini app) ----------------
def get_authed_user(init_data: str) -> dict:
    user = validate_init_data(init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Noto'g'ri yoki muddati o'tgan initData")
    return user


# ---------------- Auth helper (admin panel) ----------------
security = HTTPBasic()


def check_admin_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, ADMIN_PANEL_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, ADMIN_PANEL_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=401,
            detail="Login yoki parol noto'g'ri",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


# ---------------- API models ----------------
class OrderRequest(BaseModel):
    init_data: str
    product_id: int
    player_id: str | None = None


class MeRequest(BaseModel):
    init_data: str


# ---------------- API routes ----------------
@app.post("/api/me")
async def api_me(body: MeRequest):
    tg_user = get_authed_user(body.init_data)
    db.upsert_user(tg_user["id"], tg_user.get("username"), tg_user.get("first_name", ""))
    user = db.get_user(tg_user["id"])
    return {
        "user_id": user["user_id"],
        "username": user["username"],
        "full_name": user["full_name"],
        "phone": user["phone"],
        "balance": user["balance"],
    }


@app.get("/api/categories")
async def api_categories():
    cats = db.get_categories()
    return [dict(c) for c in cats]


@app.get("/api/categories/{category_id}/products")
async def api_products(category_id: int):
    category = db.get_category(category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    products = db.get_products(category_id)
    return {
        "category": dict(category),
        "products": [dict(p) for p in products],
    }


@app.post("/api/order")
async def api_create_order(body: OrderRequest):
    tg_user = get_authed_user(body.init_data)
    product = db.get_product(body.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")

    category = db.get_category(product["category_id"])
    if category["needs_player_id"] and not body.player_id:
        raise HTTPException(status_code=400, detail="Player ID kiritilishi shart")

    user = db.get_user(tg_user["id"])
    if not user or user["balance"] < product["price"]:
        raise HTTPException(status_code=400, detail="Balansingiz yetarli emas")

    order_id = db.create_order(tg_user["id"], product["id"], product["price"], body.player_id)

    caption = (
        f"🆕 Yangi buyurtma #{order_id}\n"
        f"Mijoz ID: {tg_user['id']} (@{tg_user.get('username', '-')})\n"
        f"Mahsulot: {product['name']} — {product['price']:,} so'm\n".replace(",", " ")
    )
    if body.player_id:
        caption += f"Player ID: {body.player_id}\n"

    from config import ADMIN_IDS
    if bot:
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, caption, reply_markup=bot_handlers.admin_order_kb(order_id))
            except Exception:
                pass

    return {"order_id": order_id, "status": "kutilmoqda"}


@app.post("/api/orders")
async def api_my_orders(body: MeRequest):
    tg_user = get_authed_user(body.init_data)
    orders = db.get_user_orders(tg_user["id"])
    result = []
    for o in orders:
        product = db.get_product(o["product_id"])
        result.append({
            "id": o["id"], "product_name": product["name"] if product else "?",
            "price": o["price"], "status": o["status"], "created_at": o["created_at"],
        })
    return result


@app.post("/api/topups")
async def api_my_topups(body: MeRequest):
    tg_user = get_authed_user(body.init_data)
    topups = db.get_user_topups(tg_user["id"])
    return [dict(t) for t in topups]


# ==================== ADMIN PANEL API ====================
class CategoryRequest(BaseModel):
    name: str
    icon_emoji: str = "🎮"
    badge: str = ""
    needs_player_id: bool = False


class ProductRequest(BaseModel):
    category_id: int
    name: str
    price: int


class StatusRequest(BaseModel):
    status: str
    admin_comment: str | None = None


@app.get("/api/admin/stats")
async def admin_stats(_: str = Depends(check_admin_auth)):
    return db.get_stats()


@app.get("/api/admin/categories")
async def admin_list_categories(_: str = Depends(check_admin_auth)):
    return [dict(c) for c in db.get_all_categories()]


@app.post("/api/admin/categories")
async def admin_add_category(body: CategoryRequest, _: str = Depends(check_admin_auth)):
    cat_id = db.add_category(body.name, body.icon_emoji, body.badge, int(body.needs_player_id))
    return {"id": cat_id}


@app.put("/api/admin/categories/{category_id}")
async def admin_edit_category(category_id: int, body: CategoryRequest, _: str = Depends(check_admin_auth)):
    if not db.get_category(category_id):
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    db.update_category(category_id, body.name, body.icon_emoji, body.badge, int(body.needs_player_id))
    return {"ok": True}


@app.delete("/api/admin/categories/{category_id}")
async def admin_delete_category(category_id: int, _: str = Depends(check_admin_auth)):
    if not db.get_category(category_id):
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    db.delete_category(category_id)
    return {"ok": True}


@app.get("/api/admin/products")
async def admin_list_products(_: str = Depends(check_admin_auth)):
    return [dict(p) for p in db.get_all_products_with_category()]


@app.post("/api/admin/products")
async def admin_add_product(body: ProductRequest, _: str = Depends(check_admin_auth)):
    if not db.get_category(body.category_id):
        raise HTTPException(status_code=404, detail="Kategoriya topilmadi")
    prod_id = db.add_product(body.category_id, body.name, body.price)
    return {"id": prod_id}


@app.put("/api/admin/products/{product_id}")
async def admin_edit_product(product_id: int, body: ProductRequest, _: str = Depends(check_admin_auth)):
    if not db.get_product(product_id):
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    db.update_product(product_id, body.name, body.price)
    return {"ok": True}


@app.delete("/api/admin/products/{product_id}")
async def admin_delete_product(product_id: int, _: str = Depends(check_admin_auth)):
    if not db.get_product(product_id):
        raise HTTPException(status_code=404, detail="Mahsulot topilmadi")
    db.delete_product(product_id)
    return {"ok": True}


@app.get("/api/admin/orders")
async def admin_list_orders(status: str | None = None, _: str = Depends(check_admin_auth)):
    return [dict(o) for o in db.get_all_orders(status)]


@app.post("/api/admin/orders/{order_id}/status")
async def admin_set_order_status(order_id: int, body: StatusRequest, _: str = Depends(check_admin_auth)):
    order = db.get_order(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Buyurtma topilmadi")
    db.set_order_status(order_id, body.status, body.admin_comment)

    if bot:
        texts = {
            "bajarildi": f"🎉 Buyurtmangiz #{order_id} yetkazib berildi!",
            "bekor_qilindi": f"❌ Buyurtmangiz #{order_id} bekor qilindi."
                              + (f"\nSabab: {body.admin_comment}" if body.admin_comment else "")
                              + f"\nTo'langan {order['price']:,} so'm balansingizga qaytarildi.".replace(",", " "),
            "kutilmoqda": f"⏳ Buyurtmangiz #{order_id} qayta ko'rib chiqilmoqda.",
        }
        text = texts.get(body.status)
        if text:
            try:
                await bot.send_message(order["user_id"], text)
            except Exception:
                pass
    return {"ok": True}


@app.get("/api/admin/topups")
async def admin_list_topups(status: str | None = None, _: str = Depends(check_admin_auth)):
    return [dict(t) for t in db.get_all_topups(status)]


@app.post("/api/admin/topups/{topup_id}/status")
async def admin_set_topup_status(topup_id: int, body: StatusRequest, _: str = Depends(check_admin_auth)):
    topup = db.get_topup(topup_id)
    if not topup:
        raise HTTPException(status_code=404, detail="To'lov topilmadi")
    db.set_topup_status(topup_id, body.status, body.admin_comment)

    if bot:
        texts = {
            "tasdiqlandi": f"✅ Balansingiz {topup['amount']:,} so'mga to'ldirildi!".replace(",", " "),
            "rad_etildi": "❌ Hisobni to'ldirish so'rovingiz rad etildi. Admin bilan bog'laning.",
        }
        text = texts.get(body.status)
        if text:
            try:
                await bot.send_message(topup["user_id"], text)
            except Exception:
                pass
    return {"ok": True}


@app.get("/admin")
async def admin_page(_: str = Depends(check_admin_auth)):
    return FileResponse("static/admin/index.html")


# ---------------- Static Mini App ----------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
