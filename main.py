import logging
import random
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, CallbackQueryHandler, CallbackContext,
    MessageHandler, Filters
)

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния игроков в памяти (в реальном проекте используйте базу данных)
players: Dict[int, Dict] = {}

# Классы персонажей
CHARACTER_CLASSES = {
    'warrior': {'health': 120, 'attack': 15, 'defense': 10},
    'mage': {'health': 80, 'attack': 25, 'defense': 5},
    'archer': {'health': 100, 'attack': 20, 'defense': 8}
}

# Противники
ENEMIES = [
    {'name': 'Гоблин', 'health': 50, 'attack': 10, 'defense': 5},
    {'name': 'Орк', 'health': 80, 'attack': 15, 'defense': 10},
    {'name': 'Дракон', 'health': 150, 'attack': 25, 'defense': 15}
]

# Награды
REWARDS = {
    'gold': (5, 20),
    'xp': (10, 30)
}

def start(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /start."""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    if chat_id not in players:
        players[chat_id] = {
            'name': user.first_name,
            'class': None,
            'level': 1,
            'xp': 0,
            'gold': 0,
            'health': 100,
            'max_health': 100,
            'attack': 10,
            'defense': 5,
            'in_combat': False
        }
        update.message.reply_text(
            f"Добро пожаловать в Random Quest, {user.first_name}!\n"
            "Выберите класс персонажа:",
            reply_markup=character_selection_keyboard()
        )
    else:
        update.message.reply_text(
            f"С возвращением, {players[chat_id]['name']}!\n"
            f"Уровень: {players[chat_id]['level']}\n"
            f"Здоровье: {players[chat_id]['health']}/{players[chat_id]['max_health']}\n"
            f"Опыт: {players[chat_id]['xp']}/100\n"
            f"Золото: {players[chat_id]['gold']}",
            reply_markup=main_menu_keyboard()
        )

def character_selection_keyboard():
    """Клавиатура для выбора класса персонажа."""
    keyboard = [
        [
            InlineKeyboardButton("Воин", callback_data='class_warrior'),
            InlineKeyboardButton("Маг", callback_data='class_mage'),
            InlineKeyboardButton("Лучник", callback_data='class_archer')
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def main_menu_keyboard():
    """Основное меню игры."""
    keyboard = [
        [InlineKeyboardButton("Отправиться в приключение", callback_data='adventure')],
        [InlineKeyboardButton("Мой персонаж", callback_data='character')],
        [InlineKeyboardButton("Магазин", callback_data='shop')]
    ]
    return InlineKeyboardMarkup(keyboard)

def button_handler(update: Update, context: CallbackContext) -> None:
    """Обработчик нажатий на кнопки."""
    query = update.callback_query
    query.answer()
    chat_id = update.effective_chat.id
    
    if chat_id not in players:
        query.edit_message_text("Пожалуйста, начните игру с помощью /start")
        return
    
    data = query.data
    
    if data.startswith('class_'):
        class_name = data.split('_')[1]
        players[chat_id]['class'] = class_name
        players[chat_id].update(CHARACTER_CLASSES[class_name])
        players[chat_id]['max_health'] = players[chat_id]['health']
        query.edit_message_text(
            f"Вы выбрали класс {class_name}!\n"
            f"Здоровье: {players[chat_id]['health']}\n"
            f"Атака: {players[chat_id]['attack']}\n"
            f"Защита: {players[chat_id]['defense']}",
            reply_markup=main_menu_keyboard()
        )
    
    elif data == 'character':
        player = players[chat_id]
        query.edit_message_text(
            f"Имя: {player['name']}\n"
            f"Класс: {player['class']}\n"
            f"Уровень: {player['level']}\n"
            f"Опыт: {player['xp']}/100\n"
            f"Здоровье: {player['health']}/{player['max_health']}\n"
            f"Атака: {player['attack']}\n"
            f"Защита: {player['defense']}\n"
            f"Золото: {player['gold']}",
            reply_markup=main_menu_keyboard()
        )
    
    elif data == 'adventure':
        if players[chat_id]['in_combat']:
            query.edit_message_text("Вы уже в бою!", reply_markup=combat_keyboard())
            return
        
        # 30% шанс найти противника
        if random.random() < 0.3:
            enemy = random.choice(ENEMIES).copy()
            players[chat_id]['in_combat'] = True
            players[chat_id]['current_enemy'] = enemy
            query.edit_message_text(
                f"Вы встретили {enemy['name']}!\n"
                f"Здоровье врага: {enemy['health']}\n"
                f"Атака врага: {enemy['attack']}\n"
                f"Защита врага: {enemy['defense']}",
                reply_markup=combat_keyboard()
            )
        else:
            gold_gained = random.randint(*REWARDS['gold'])
            players[chat_id]['gold'] += gold_gained
            query.edit_message_text(
                f"Вы исследовали местность и нашли {gold_gained} золота!\n"
                "Продолжить приключения?",
                reply_markup=main_menu_keyboard()
            )
    
    elif data == 'attack':
        if not players[chat_id]['in_combat']:
            query.edit_message_text("Сейчас нет боя!", reply_markup=main_menu_keyboard())
            return
        
        player = players[chat_id]
        enemy = player['current_enemy']
        
        # Игрок атакует
        player_damage = max(1, player['attack'] - enemy['defense'] // 2)
        enemy['health'] -= player_damage
        
        # Проверка победы
        if enemy['health'] <= 0:
            xp_gained = random.randint(*REWARDS['xp'])
            gold_gained = random.randint(*REWARDS['gold'])
            player['xp'] += xp_gained
            player['gold'] += gold_gained
            player['in_combat'] = False
            
            # Проверка уровня
            if player['xp'] >= 100:
                player['level'] += 1
                player['xp'] = 0
                player['max_health'] += 10
                player['health'] = player['max_health']
                player['attack'] += 2
                player['defense'] += 1
                level_up_msg = "\nВы достигли нового уровня!"
            else:
                level_up_msg = ""
            
            query.edit_message_text(
                f"Вы победили {enemy['name']} и получили:\n"
                f"{xp_gained} опыта и {gold_gained} золота!{level_up_msg}",
                reply_markup=main_menu_keyboard()
            )
            return
        
        # Враг атакует
        enemy_damage = max(1, enemy['attack'] - player['defense'] // 2)
        player['health'] -= enemy_damage
        
        # Проверка поражения
        if player['health'] <= 0:
            player['health'] = 1  # Оставляем 1 HP вместо смерти
            player['in_combat'] = False
            query.edit_message_text(
                "Вы проиграли бой и чудом выжили!\n"
                "Вам нужно восстановиться.",
                reply_markup=main_menu_keyboard()
            )
            return
        
        query.edit_message_text(
            f"Вы нанесли {player_damage} урона. {enemy['name']}: {enemy['health']} HP\n"
            f"{enemy['name']} нанес вам {enemy_damage} урона. Ваше здоровье: {player['health']}/{player['max_health']}",
            reply_markup=combat_keyboard()
        )
    
    elif data == 'flee':
        if not players[chat_id]['in_combat']:
            query.edit_message_text("Сейчас нет боя!", reply_markup=main_menu_keyboard())
            return
        
        # 50% шанс успешно сбежать
        if random.random() < 0.5:
            players[chat_id]['in_combat'] = False
            query.edit_message_text(
                "Вы успешно сбежали от противника!",
                reply_markup=main_menu_keyboard()
            )
        else:
            player = players[chat_id]
            enemy = player['current_enemy']
            enemy_damage = max(1, enemy['attack'] - player['defense'] // 2)
            player['health'] -= enemy_damage
            
            if player['health'] <= 0:
                player['health'] = 1
                players[chat_id]['in_combat'] = False
                query.edit_message_text(
                    "Вы не смогли сбежать и были повержены!\n"
                    "Чудом вам удалось выжить, но вы сильно ранены.",
                    reply_markup=main_menu_keyboard()
                )
            else:
                query.edit_message_text(
                    f"Вы не смогли сбежать! {enemy['name']} нанес вам {enemy_damage} урона.\n"
                    f"Ваше здоровье: {player['health']}/{player['max_health']}",
                    reply_markup=combat_keyboard()
                )

def combat_keyboard():
    """Клавиатура для боя."""
    keyboard = [
        [InlineKeyboardButton("Атаковать", callback_data='attack')],
        [InlineKeyboardButton("Сбежать", callback_data='flee')]
    ]
    return InlineKeyboardMarkup(keyboard)

def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help."""
    update.message.reply_text(
        "Random Quest - простая RPG игра в Telegram.\n"
        "Команды:\n"
        "/start - начать игру\n"
        "/help - показать это сообщение\n"
        "Используйте кнопки для взаимодействия с игрой."
    )

def main() -> None:
    """Запуск бота."""
    # Создаем Updater и передаем ему токен бота
    updater = Updater("TOKEN")
    
    # Получаем диспетчер для регистрации обработчиков
    dispatcher = updater.dispatcher
    
    # Регистрируем обработчики команд
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("help", help_command))
    
    # Регистрируем обработчик нажатий на кнопки
    dispatcher.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()