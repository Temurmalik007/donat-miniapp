import asyncio
import contextlib
import logging

from fastapi import FastAPI, Request, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

import database as db
from config import BOT_TOKEN, PORT
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


# ---------------- Auth helper ----------------
def get_authed_user(init_data: str) -> dict:
    user = validate_init_data(init_data)
    if not user:
        raise HTTPException(status_code=401, detail="Noto'g'ri yoki muddati o'tgan initData")
    return user


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


# ---------------- Static Mini App ----------------
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
async def index():
    return FileResponse("static/index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)
