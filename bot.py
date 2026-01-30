import os
import time
import telebot
from telebot import types

BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing")

bot = telebot.TeleBot(BOT_TOKEN)
user_data = {}

ACTIVITY_FACTORS = {
    "Минимальный — сидячая работа, отсутствие спорта, редкие прогулки.": 1.2,
    "Низкий — лёгкие тренировки 1–3 раза в неделю или работа «на ногах».": 1.375,
    "Умеренный — спорт 3–5 раз в неделю или физический труд.": 1.55,
    "Высокий — тренировки 6–7 раз в неделю или тяжёлая работа.": 1.725,
    "Экстремальный — проф. спорт/очень большие нагрузки.": 1.9,
}

DEFICIT = 0.15
SURPLUS = 0.10


def is_number(text: str) -> bool:
    try:
        float(text.replace(",", "."))
        return True
    except ValueError:
        return False


def kbju_from_calories(calories: float):
    protein_g = (calories * 0.30) / 4
    fat_g = (calories * 0.30) / 9
    carb_g = (calories * 0.40) / 4
    return protein_g, fat_g, carb_g

def show_menu(chat_id: int):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔁 Пересчитать", "ℹ️ Помощь")
    bot.send_message(chat_id, "Возникли вопросы? Мы поможем: @Iron_Curtain54", reply_markup=markup)

def show_offer(chat_id: int):
    bot.send_message(chat_id, "Хотите индивидуальный план питания? Подберём рацион с учетом ваших целей и предпочтений:@Iron_Curtain54")

def reset_flow(chat_id: int):
    # Сбрасываем "ожидания шагов" и временные данные
    bot.clear_step_handler_by_chat_id(chat_id)
    user_data[chat_id] = {}


@bot.message_handler(commands=["start", "restart"])
def start(message):
    reset_flow(message.chat.id)
    bot.send_message(message.chat.id, "Железный Занавес на связи! 😎", reply_markup=types.ReplyKeyboardRemove())
    msg = bot.send_message(message.chat.id, "Давайте рассчитаем Ващи КБЖУ")
    msg = bot.send_message(message.chat.id, "Какой у вас рост (см)?")
    bot.register_next_step_handler(msg, get_height)

@bot.message_handler(func=lambda m: m.text in ["🔁 Пересчитать", "ℹ️ Помощь"])
def handle_menu_buttons(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)
    if message.text == "🔁 Пересчитать":
        start(message)
    else:
        bot.send_message(
            message.chat.id,
            "Команды:\n"
            "/start или /restart — начать заново\n"
        )
        show_menu(message.chat.id)


def get_height(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)

    txt = message.text.strip()
    if not is_number(txt):
        msg = bot.send_message(message.chat.id, "Введите рост числом, например: 170")
        bot.register_next_step_handler(msg, get_height)
        return

    user_data[message.chat.id]["height"] = float(txt.replace(",", "."))

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    markup.add("Мужской", "Женский")
    msg = bot.send_message(message.chat.id, "Укажите пол", reply_markup=markup)
    bot.register_next_step_handler(msg, get_gender)


def get_gender(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)

    gender = message.text.strip()
    if gender not in ("Мужской", "Женский"):
        msg = bot.send_message(message.chat.id, "Выбери кнопкой: Мужской или Женский")
        bot.register_next_step_handler(msg, get_gender)
        return

    user_data[message.chat.id]["gender"] = gender

    msg = bot.send_message(message.chat.id, "Укажите вес (кг)", reply_markup=types.ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, get_weight)


def get_weight(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)

    txt = message.text.strip()
    if not is_number(txt):
        msg = bot.send_message(message.chat.id, "Введите вес числом, например: 65")
        bot.register_next_step_handler(msg, get_weight)
        return

    user_data[message.chat.id]["weight"] = float(txt.replace(",", "."))

    msg = bot.send_message(message.chat.id, "Возраст (полных лет)")
    bot.register_next_step_handler(msg, get_age)


def get_age(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)

    txt = message.text.strip()
    if not txt.isdigit():
        msg = bot.send_message(message.chat.id, "Введите возраст целым числом, например: 25")
        bot.register_next_step_handler(msg, get_age)
        return

    age = int(txt)
    if age < 5 or age > 110:
        msg = bot.send_message(message.chat.id, "Возраст выглядит странно 🙂 Введите число от 5 до 110.")
        bot.register_next_step_handler(msg, get_age)
        return

    user_data[message.chat.id]["age"] = age

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for k in ACTIVITY_FACTORS.keys():
        markup.add(k)

    msg = bot.send_message(message.chat.id, "Выберите уровень активности:", reply_markup=markup)
    bot.register_next_step_handler(msg, get_activity)


def get_activity(message):
    bot.clear_step_handler_by_chat_id(message.chat.id)

    choice = message.text.strip()
    if choice not in ACTIVITY_FACTORS:
        msg = bot.send_message(message.chat.id, "Выбери вариант кнопкой из списка 🙂")
        bot.register_next_step_handler(msg, get_activity)
        return

    user_data[message.chat.id]["activity"] = ACTIVITY_FACTORS[choice]

    h = user_data[message.chat.id]["height"]
    w = user_data[message.chat.id]["weight"]
    a = user_data[message.chat.id]["age"]
    g = user_data[message.chat.id]["gender"]
    k = user_data[message.chat.id]["activity"]

    if g == "Мужской":
        bmr = 10 * w + 6.25 * h - 5 * a + 5
    else:
        bmr = 10 * w + 6.25 * h - 5 * a - 161

    tdee_maint = bmr * k
    tdee_cut = tdee_maint * (1 - DEFICIT)
    tdee_bulk = tdee_maint * (1 + SURPLUS)

    p_m, f_m, c_m = kbju_from_calories(tdee_maint)
    p_c, f_c, c_c = kbju_from_calories(tdee_cut)
    p_b, f_b, c_b = kbju_from_calories(tdee_bulk)

    bot.send_message(message.chat.id, "Готово ✅", reply_markup=types.ReplyKeyboardRemove())

    bot.send_message(
        message.chat.id,
        "Твои ориентиры по КБЖУ:\n\n"
        f"1) Поддержание: {tdee_maint:.0f} ккал\n"
        f"   Б: {p_m:.0f} г  Ж: {f_m:.0f} г  У: {c_m:.0f} г\n\n"
        f"2) Снижение (-{int(DEFICIT*100)}%): {tdee_cut:.0f} ккал\n"
        f"   Б: {p_c:.0f} г  Ж: {f_c:.0f} г  У: {c_c:.0f} г\n\n"
        f"3) Набор (+{int(SURPLUS*100)}%): {tdee_bulk:.0f} ккал\n"
        f"   Б: {p_b:.0f} г  Ж: {f_b:.0f} г  У: {c_b:.0f} г\n"
    )

    show_offer(message.chat.id)

bot.remove_webhook()
time.sleep(1)
bot.infinity_polling(timeout=10, long_polling_timeout=5, skip_pending=True)

