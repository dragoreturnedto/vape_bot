import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# ===== ЛОГИ =====
logging.basicConfig(level=logging.INFO)

# ===== ТОКЕН =====
BOT_TOKEN = os.environ.get("TG_TOKEN")
if not BOT_TOKEN:
    print("TG_TOKEN не найден в переменных окружения!")
    raise SystemExit(1)

# ===== ДОСТУП =====
ALLOWED_USERS = {123456789}  # <-- ВСТАВЬ СВОЙ Telegram user_id

# ===== ИНИЦИАЛИЗАЦИЯ =====
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# ===== КЛАВИАТУРЫ =====
def main_menu_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(
        InlineKeyboardButton("🛍 Каталог", callback_data="menu_catalog"),
        InlineKeyboardButton("🛒 Сделать заказ", callback_data="order_start"),
        InlineKeyboardButton("☎ Контакты", callback_data="menu_contacts"),
        InlineKeyboardButton("💸 Скидки", callback_data="menu_discounts"),
        InlineKeyboardButton("❓ Почему мы?", callback_data="menu_why")
    )
    return kb

def back_menu_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("« Назад в меню", callback_data="menu_main"))
    return kb

def order_or_back_kb():
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 Сделать заказ", callback_data="order_start"))
    kb.add(InlineKeyboardButton("« Назад в меню", callback_data="menu_main"))
    return kb

# ===== FSM =====
class OrderForm(StatesGroup):
    items = State()
    address = State()
    when = State()

# ===== ХЕНДЛЕРЫ С ОГРАНИЧЕНИЕМ ПО user_id =====
@dp.message_handler(commands=["start", "menu"], user_id=ALLOWED_USERS)
async def cmd_start(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@dp.message_handler(commands=["help"], user_id=ALLOWED_USERS)
async def cmd_help(message: types.Message):
    await message.answer(
        "Команды:\n"
        "/start — главное меню\n"
        "/menu — главное меню\n"
        "/help — помощь\n"
        "/setdiscounts — обновить раздел «Скидки» (только админ)"
    )

@dp.callback_query_handler(lambda c: c.data == "menu_main", state="*", user_id=ALLOWED_USERS)
async def cb_main(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    try:
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    except Exception:
        await cb.message.answer("Главное меню:", reply_markup=main_menu_kb())
    await cb.answer()

@dp.callback_query_handler(lambda c: c.data == "menu_catalog", state="*", user_id=ALLOWED_USERS)
async def cb_catalog(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer("Каталог пока пуст (демо).", reply_markup=order_or_back_kb())

@dp.callback_query_handler(lambda c: c.data == "menu_contacts", state="*", user_id=ALLOWED_USERS)
async def cb_contacts(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer("☎ Поддержка: @Dragoreturnedto", reply_markup=back_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "menu_why", state="*", user_id=ALLOWED_USERS)
async def cb_why(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer(
        "❓ <b>Почему мы?</b>\n"
        "• Самая быстрая доставка в Риге 🚚\n"
        "• Всегда новые позиции 🔥\n"
        "• Вежливая поддержка и помощь с выбором",
        reply_markup=back_menu_kb()
    )

@dp.callback_query_handler(lambda c: c.data == "menu_discounts", state="*", user_id=ALLOWED_USERS)
async def cb_discounts(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer("💸 <b>Скидки</b>\nСейчас активных скидок нет. Заглядывайте позже 😉",
                            reply_markup=back_menu_kb())

@dp.callback_query_handler(lambda c: c.data == "order_start", state="*", user_id=ALLOWED_USERS)
async def order_start(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer(
        "🛒 <b>Сделать заказ</b>\n"
        "Напишите товары, которые выбрали (название и количество). Пример:\n"
        "<i>ElfBar BC5000 — 2 шт; Жидкость Salt 30мл — 1 шт (манго)</i>",
        reply_markup=back_menu_kb()
    )
    await OrderForm.items.set()

@dp.message_handler(state=OrderForm.items, user_id=ALLOWED_USERS)
async def order_got_items(message: types.Message, state: FSMContext):
    await state.update_data(items=message.text.strip())
    await message.answer("Отлично! Теперь укажите <b>адрес доставки</b> (улица, дом, подъезд/этаж).")
    await OrderForm.address.set()

@dp.message_handler(state=OrderForm.address, user_id=ALLOWED_USERS)
async def order_got_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await message.answer("И последнее — напишите <b>дату и время</b> доставки (например: сегодня 19:30).")
    await OrderForm.when.set()

@dp.message_handler(state=OrderForm.when, user_id=ALLOWED_USERS)
async def order_got_when(message: types.Message, state: FSMContext):
    data = await state.get_data()
    items = data.get("items", "—")
    address = data.get("address", "—")
    when = message.text.strip()

    text = (
        "🆕 <b>Новый заказ</b>\n"
        f"👤 Пользователь: <a href='tg://user?id={message.from_user.id}'>{message.from_user.full_name}</a> (@{message.from_user.username or '—'})\n"
        f"🛍 Позиции: {items}\n"
        f"📍 Адрес: {address}\n"
        f"⏰ Время: {when}\n"
        f"🆔 User ID: <code>{message.from_user.id}</code>"
    )
    try:
        await bot.send_message(-1003264765078, text)  # ORDERS_CHAT_ID
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить заказ. Проверь, что бот добавлен в чат.\n\n{e}")

    await message.answer("Спасибо! Заявка отправлена ✅", reply_markup=main_menu_kb())
    await state.finish()

# ===== ЗАПУСК =====
if __name__ == "__main__":
    print("DEBUG TOKEN:", BOT_TOKEN)  # на Railway видно в логах, для контроля
    executor.start_polling(dp, skip_updates=True)

