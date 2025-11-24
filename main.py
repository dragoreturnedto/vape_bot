import os
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup

# === ТОКЕН ===
BOT_TOKEN = os.environ.get("TG_TOKEN")

# === НАСТРОЙКИ ===
CATALOG_FROM_CHAT_ID = -1003264765078   # канал, где лежит сообщение каталога
# ID сообщения из ссылки https://t.me/c/3264765078/29  ->  29
CATALOG_MESSAGE_IDS = [29]              # список сообщений для копирования
ORDERS_CHAT_ID = -1003264765078         # куда бот шлёт заявки
SUPPORT_USERNAME = "Dragoreturnedto"    # админ
DISCOUNTS_FILE = "discounts.txt"

# === ИНИЦИАЛИЗАЦИЯ ===
bot = Bot(token=BOT_TOKEN, parse_mode="HTML")
dp = Dispatcher(bot, storage=MemoryStorage())

# === КЛАВИАТУРЫ ===
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

def get_discounts_text():
    if os.path.exists(DISCOUNTS_FILE):
        with open(DISCOUNTS_FILE, "r", encoding="utf-8") as f:
            t = f.read().strip()
            if t:
                return t
    return "Сейчас активных скидок нет. Заглядывайте позже 😉"

# === FSM ===
class OrderForm(StatesGroup):
    items = State()
    address = State()
    when = State()

# === КОМАНДЫ ===
@dp.message_handler(commands=["start", "menu"])
async def cmd_start(message: types.Message):
    await message.answer("Главное меню:", reply_markup=main_menu_kb())

@dp.message_handler(commands=["help"])
async def cmd_help(message: types.Message):
    await message.answer(
        "Команды:\n"
        "/start — главное меню\n"
        "/menu — главное меню\n"
        "/help — помощь\n"
        "/setdiscounts — обновить раздел «Скидки» (только админ)"
    )

# === НАЗАД В МЕНЮ ===
@dp.callback_query_handler(lambda c: c.data == "menu_main", state="*")
async def cb_main(cb: types.CallbackQuery, state: FSMContext):
    try:
        await state.finish()
    except Exception:
        pass
    try:
        await cb.message.edit_text("Главное меню:", reply_markup=main_menu_kb())
    except Exception:
        await cb.message.answer("Главное меню:", reply_markup=main_menu_kb())
    await cb.answer()

# === КАТАЛОГ ===
@dp.callback_query_handler(lambda c: c.data == "menu_catalog", state="*")
async def cb_catalog(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()

    for mid in CATALOG_MESSAGE_IDS:
        try:
            await bot.copy_message(
                chat_id=cb.message.chat.id,
                from_chat_id=CATALOG_FROM_CHAT_ID,
                message_id=mid
            )
        except Exception as e:
            await cb.message.answer(
                f"⚠️ Не удалось скопировать сообщение {mid}.\n"
                f"Проверь, что бот добавлен в канал и имеет доступ к сообщениям.\n\n{e}"
            )
            break

    await cb.message.answer("Выше — актуальные позиции. Можно оформить заказ:", reply_markup=order_or_back_kb())

# === КОНТАКТЫ ===
@dp.callback_query_handler(lambda c: c.data == "menu_contacts", state="*")
async def cb_contacts(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer(f"☎ Поддержка: @{SUPPORT_USERNAME}", reply_markup=back_menu_kb())

# === ПОЧЕМУ МЫ ===
@dp.callback_query_handler(lambda c: c.data == "menu_why", state="*")
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

# === СКИДКИ ===
@dp.callback_query_handler(lambda c: c.data == "menu_discounts", state="*")
async def cb_discounts(cb: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await cb.answer()
    await cb.message.answer("💸 <b>Скидки</b>\n" + get_discounts_text(), reply_markup=back_menu_kb())

# === ОФОРМЛЕНИЕ ЗАКАЗА ===
@dp.callback_query_handler(lambda c: c.data == "order_start", state="*")
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

@dp.message_handler(state=OrderForm.items)
async def order_got_items(message: types.Message, state: FSMContext):
    await state.update_data(items=message.text.strip())
    await message.answer("Отлично! Теперь укажите <b>адрес доставки</b> (улица, дом, подъезд/этаж).")
    await OrderForm.address.set()

@dp.message_handler(state=OrderForm.address)
async def order_got_address(message: types.Message, state: FSMContext):
    await state.update_data(address=message.text.strip())
    await message.answer("И последнее — напишите <b>дату и время</b> доставки (например: сегодня 19:30).")
    await OrderForm.when.set()

@dp.message_handler(state=OrderForm.when)
async def order_got_when(message: types.Message, state: FSMContext):
    user = message.from_user
    data = await state.get_data()
    items = data.get("items", "—")
    address = data.get("address", "—")
    when = message.text.strip()

    text = (
        "🆕 <b>Новый заказ</b>\n"
        f"👤 Пользователь: <a href='tg://user?id={user.id}'>{user.full_name}</a> (@{user.username or '—'})\n"
        f"🛍 Позиции: {items}\n"
        f"📍 Адрес: {address}\n"
        f"⏰ Время: {when}\n"
        f"🆔 User ID: <code>{user.id}</code>"
    )

    try:
        await bot.send_message(ORDERS_CHAT_ID, text)
    except Exception as e:
        await message.answer(f"⚠️ Не удалось отправить заказ. Проверь, что бот добавлен в чат.\n\n{e}")

    await message.answer("Спасибо! Заявка отправлена ✅", reply_markup=main_menu_kb())
    await state.finish()

# === АДМИН: СКИДКИ ===
@dp.message_handler(commands=["setdiscounts"])
async def cmd_set_discounts(message: types.Message):
    if (message.from_user.username or "").lower() != SUPPORT_USERNAME.lower():
        await message.answer("Эта команда доступна только администратору.")
        return
    args = message.get_args()
    if not args:
        await message.answer("Использование: <code>/setdiscounts текст скидок</code>")
        return
    with open(DISCOUNTS_FILE, "w", encoding="utf-8") as f:
        f.write(args)
    await message.answer("Текст скидок обновлён ✅")

# === ЗАПУСК ===
if __name__ == "__main__":
    print("Бот запущен ✅")
    executor.start_polling(dp, skip_updates=True)
