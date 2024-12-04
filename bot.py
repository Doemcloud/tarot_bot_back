import asyncio
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.exceptions import TelegramBadRequest
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from config import TOKEN, CHANNEL_USERNAME  # Токен бота и имя канала

# Инициализация бота и диспетчера
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Функция для загрузки данных из JSON
def load_json(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


# Загружаем данные карт и сообщений
cards_data = load_json("data/cards.json")  # Данные о картах
schedule_data = load_json("data/schedule.json")  # Данные для запланированных сообщений


# Проверка подписки на канал
async def check_subscription(user_id):
    try:
        # Получаем статус пользователя в канале
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)

        # Выводим отладочную информацию о статусе подписки
        print(f"User {user_id} status: {member.status}")

        # Проверяем статус пользователя
        return member.status in ["member", "administrator", "creator"]
    except TelegramBadRequest as e:
        # Выводим ошибку, если произошла ошибка с запросом
        print(f"Error while checking subscription: {e}")
        return False


# Обработчик команды /start
async def start_command(message: Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if not is_subscribed:
        # Создаем клавиатуру с кнопкой для подписки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton(text="Проверить подписку", callback_data="check_subscription")]
            ]
        )
        await message.reply(
            f"Чтобы пользоваться ботом, подпишитесь на канал: @{CHANNEL_USERNAME}",
            reply_markup=keyboard
        )
        return
    # Кнопка для перехода в Web App с картами
    web_app_button = InlineKeyboardButton(
        text="Перейти в веб-приложение",
        web_app=types.WebAppInfo(url="https://24tarot.ru")  # Передаем через именованный аргумент
    )
    keyboard = InlineKeyboardMarkup(inline_keyboard=[[web_app_button]])

    await message.reply("Привет! Я бот для раскладов Таро. Выберите действие из меню.", reply_markup=keyboard)

# Обработчик команды /tarot
async def tarot_command(message: Message):
    is_subscribed = await check_subscription(message.from_user.id)
    if not is_subscribed:
        # Создаем клавиатуру с кнопкой для подписки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("Проверить подписку", callback_data="check_subscription")]
            ]
        )
        await message.reply(
            f"Чтобы пользоваться ботом, подпишитесь на канал: @{CHANNEL_USERNAME}",
            reply_markup=keyboard
        )
        return

    # Создание клавиатуры с картами
    keyboard = InlineKeyboardMarkup(row_width=2)
    for card_id, card in cards_data.items():
        keyboard.add(InlineKeyboardButton(card["name"], callback_data=f"card_{card_id}"))
    await message.reply("Выберите карту:", reply_markup=keyboard)


# Обработчик выбора карты
async def card_selected(callback_query: CallbackQuery):
    is_subscribed = await check_subscription(callback_query.from_user.id)
    if not is_subscribed:
        # Отправляем сообщение о необходимости подписки
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("Проверить подписку", callback_data="check_subscription")]
            ]
        )
        await callback_query.message.answer(
            f"Чтобы пользоваться ботом, подпишитесь на канал: @{CHANNEL_USERNAME}",
            reply_markup=keyboard
        )
        await callback_query.answer()
        return

    card_id = callback_query.data.split("_")[1]
    card = cards_data.get(card_id)
    if card:
        with open(card["image"], "rb") as image_file:
            await bot.send_photo(callback_query.from_user.id, image_file,
                                 caption=f"**{card['name']}**\n\n{card['description']}")
    await callback_query.answer()


# Обработчик кнопки "Проверить подписку"
async def check_subscription_callback(callback_query: CallbackQuery):
    is_subscribed = await check_subscription(callback_query.from_user.id)
    if is_subscribed:
        await callback_query.message.answer("Вы уже подписаны на канал!")
    else:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton("Подписаться", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("Проверить подписку", callback_data="check_subscription")]
            ]
        )
        await callback_query.message.answer(
            f"Вы не подписаны на канал @{CHANNEL_USERNAME}. Подпишитесь, чтобы продолжить.",
            reply_markup=keyboard
        )
    await callback_query.answer()


# Запланированная рассылка
async def send_scheduled_messages():
    today = datetime.now().strftime("%Y-%m-%d")
    for message in schedule_data["messages"]:
        if message["date"] == today:
            # Укажите ID чата или список чатов для рассылки
            await bot.send_message(chat_id="ВАШ_ЧАТ_ID", text=message["text"])


# Создание планировщика и запуск
scheduler = AsyncIOScheduler()


async def start_scheduler():
    scheduler.add_job(send_scheduled_messages, "cron", hour=10)  # Запускать в 10:00 ежедневно
    scheduler.start()


# Регистрация обработчиков с фильтром команд
dp.message.register(start_command, F.text == "/start")
dp.message.register(tarot_command, F.text == "/tarot")
dp.callback_query.register(card_selected, F.data.startswith("card_"))
dp.callback_query.register(check_subscription_callback, F.data == "check_subscription")


# Асинхронный запуск
async def main():
    print("Бот запущен!")
    # Запускаем планировщик
    await start_scheduler()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())