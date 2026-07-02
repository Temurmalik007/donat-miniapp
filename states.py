from aiogram.fsm.state import State, StatesGroup


class TopupFlow(StatesGroup):
    waiting_amount = State()
    waiting_method = State()
    waiting_receipt = State()


class AdminFlow(StatesGroup):
    waiting_category_name = State()
    waiting_category_icon = State()
    waiting_category_badge = State()
    waiting_category_needs_id = State()
    waiting_product_category = State()
    waiting_product_name = State()
    waiting_product_price = State()
    waiting_reject_reason = State()
