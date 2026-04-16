from telegram import ReplyKeyboardMarkup


def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["Баланс"],
            ["Расход", "Приход"],
            ["История"],
        ],
        resize_keyboard=True,
    )
