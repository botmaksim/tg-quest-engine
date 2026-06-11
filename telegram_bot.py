import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import json
import random
import os
import glob
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("Make sure the token is set in the .env file (BOT_TOKEN=your_token)")

bot = telebot.TeleBot(TOKEN)

# Load all quests
loaded_quests = {}
quest_files = glob.glob('quests/*.json')
for file_path in quest_files:
    if file_path.endswith('.example'):
        continue
    quest_id = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, 'r', encoding='utf-8') as f:
        loaded_quests[quest_id] = json.load(f)

print(f"Quests loaded: {len(loaded_quests)}")

user_states = {}

def get_quest_data(chat_id):
    active_quest_id = user_states[chat_id].get('active_quest')
    if not active_quest_id or active_quest_id not in loaded_quests:
        return None
    return loaded_quests[active_quest_id]

def get_state(chat_id):
    return user_states[chat_id]['state']

def cleanup_chat(chat_id):
    if chat_id in user_states and 'cleanup_messages' in user_states[chat_id]:
        for msg_id in user_states[chat_id]['cleanup_messages']:
            try:
                bot.delete_message(chat_id, msg_id)
            except Exception:
                pass
        user_states[chat_id]['cleanup_messages'] = []

def track_cleanup(chat_id, message_id):
    if chat_id in user_states:
        if 'cleanup_messages' not in user_states[chat_id]:
            user_states[chat_id]['cleanup_messages'] = []
        if message_id not in user_states[chat_id]['cleanup_messages']:
            user_states[chat_id]['cleanup_messages'].append(message_id)

def eval_text(text_block, state):
    if isinstance(text_block, str):
        return text_block
    if isinstance(text_block, list):
        for item in text_block:
            condition = item.get('condition')
            if condition:
                try:
                    if eval(condition, {"state": state}):
                        return item.get('value', '')
                except Exception as e:
                    print(f"Error evaluating condition '{condition}': {e}")
                    continue
            if item.get('default'):
                return item.get('value', '')
    return ""

def send_scene(chat_id):
    state = get_state(chat_id)
    quest_data = get_quest_data(chat_id)
    scene_id = state.get('scene', 'scene_1')
    
    if scene_id not in quest_data['scenes']:
        bot.send_message(chat_id, "Error: scene not found!")
        return

    scene_info = quest_data['scenes'][scene_id]
    text = eval_text(scene_info.get('text', ''), state)

    markup = InlineKeyboardMarkup(row_width=1)
    for idx, opt in enumerate(scene_info.get('options', [])):
        btn_text = eval_text(opt.get('text', ''), state)
        if btn_text:
            markup.add(InlineKeyboardButton(btn_text, callback_data=f"opt|{scene_id}|{idx}"))

    bot.send_message(chat_id, text, reply_markup=markup)
    
    if scene_id == 'epilogue':
        track_ending(chat_id, text)

def track_ending(chat_id, ending_text):
    state = get_state(chat_id)
    quest_data = get_quest_data(chat_id)
    active_quest = user_states[chat_id]['active_quest']
    
    ending_id = hash(ending_text)
    user_states[chat_id]['unlocked_endings'][active_quest].add(ending_id)
    
    unlocked = len(user_states[chat_id]['unlocked_endings'][active_quest])
    total = quest_data.get('total_endings', 0)
    if total > 0:
        msg = bot.send_message(chat_id, f"🏆 Endings unlocked: {unlocked}/{total}")
        track_cleanup(chat_id, msg.message_id)

def trigger_ending(chat_id, text, sticker_id=None):
    msg = bot.send_message(chat_id, f"💀 {text}")
    track_cleanup(chat_id, msg.message_id)
    
    if sticker_id:
        try:
            msg = bot.send_sticker(chat_id, sticker_id)
            track_cleanup(chat_id, msg.message_id)
        except telebot.apihelper.ApiTelegramException:
            msg = bot.send_message(chat_id, f"[Sticker placeholder: {sticker_id}]")
            track_cleanup(chat_id, msg.message_id)
            
    track_ending(chat_id, text)
            
    markup = InlineKeyboardMarkup(row_width=1).add(InlineKeyboardButton("🔄 Restart", callback_data="restart"))
    msg = bot.send_message(chat_id, "Game over.", reply_markup=markup)
    track_cleanup(chat_id, msg.message_id)

@bot.message_handler(commands=['start'])
def start_quest(message):
    chat_id = message.chat.id
    cleanup_chat(chat_id)
    
    if not loaded_quests:
        bot.send_message(chat_id, "No quests loaded!")
        return
        
    if chat_id not in user_states:
        user_states[chat_id] = {'active_quest': None, 'state': {}, 'unlocked_endings': {}, 'cleanup_messages': []}
        
    if len(loaded_quests) == 1:
        quest_id = list(loaded_quests.keys())[0]
        start_specific_quest(chat_id, quest_id)
    else:
        markup = InlineKeyboardMarkup(row_width=1)
        for q_id, q_data in loaded_quests.items():
            title = q_data.get('title', q_id)
            markup.add(InlineKeyboardButton(title, callback_data=f"start_quest|{q_id}"))
        bot.send_message(chat_id, "Choose a quest to play:", reply_markup=markup)

def start_specific_quest(chat_id, quest_id):
    if quest_id not in loaded_quests:
        return
        
    quest_data = loaded_quests[quest_id]
    
    if chat_id not in user_states:
        user_states[chat_id] = {'active_quest': None, 'state': {}, 'unlocked_endings': {}, 'cleanup_messages': []}
        
    if quest_id not in user_states[chat_id]['unlocked_endings']:
        user_states[chat_id]['unlocked_endings'][quest_id] = set()
        
    user_states[chat_id]['active_quest'] = quest_id
    user_states[chat_id]['state'] = dict(quest_data.get('initial_state', {}))
    
    welcome_text = quest_data.get('initial_message', 'Welcome to the game!')
    bot.send_message(chat_id, welcome_text)
    send_scene(chat_id)

@bot.message_handler(commands=['endings'])
def check_endings(message):
    chat_id = message.chat.id
    if chat_id not in user_states or not user_states[chat_id].get('active_quest'):
        bot.send_message(chat_id, "You haven't started a quest yet. Use /choose or /start")
        return
        
    quest_data = get_quest_data(chat_id)
    active_quest = user_states[chat_id]['active_quest']
    unlocked = len(user_states[chat_id]['unlocked_endings'].get(active_quest, set()))
    total = quest_data.get('total_endings', 0)
    title = quest_data.get('title', active_quest)
    
    if total > 0:
        bot.send_message(chat_id, f"🏆 Endings unlocked for '{title}': {unlocked}/{total}")
    else:
        bot.send_message(chat_id, f"🏆 Endings unlocked for '{title}': {unlocked}")

@bot.message_handler(commands=['choose'])
def choose_quest(message):
    chat_id = message.chat.id
    cleanup_chat(chat_id)
    
    if not loaded_quests:
        bot.send_message(chat_id, "No quests loaded!")
        return
        
    if chat_id not in user_states:
        user_states[chat_id] = {'active_quest': None, 'state': {}, 'unlocked_endings': {}, 'cleanup_messages': []}
        
    markup = InlineKeyboardMarkup(row_width=1)
    for q_id, q_data in loaded_quests.items():
        title = q_data.get('title', q_id)
        markup.add(InlineKeyboardButton(title, callback_data=f"start_quest|{q_id}"))
    bot.send_message(chat_id, "Choose a quest to play:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('start_quest|') or call.data.startswith('opt|') or call.data == 'restart')
def handle_option(call):
    chat_id = call.message.chat.id
    
    if call.data.startswith('start_quest|'):
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except Exception:
            bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)
        _, quest_id = call.data.split('|')
        start_specific_quest(chat_id, quest_id)
        return

    if call.data == 'restart':
        cleanup_chat(chat_id)
        active_quest = user_states[chat_id].get('active_quest')
        if active_quest:
            quest_data = loaded_quests[active_quest]
            user_states[chat_id]['state'] = dict(quest_data.get('initial_state', {}))
            send_scene(chat_id)
        return

    try:
        bot.delete_message(chat_id, call.message.message_id)
    except Exception:
        bot.edit_message_reply_markup(chat_id, call.message.message_id, reply_markup=None)

    quest_data = get_quest_data(chat_id)
    if not quest_data:
        return
        
    state = get_state(chat_id)
    _, scene_id, opt_idx = call.data.split('|')
    opt_idx = int(opt_idx)
    
    if scene_id not in quest_data['scenes']:
        return
        
    options = quest_data['scenes'][scene_id].get('options', [])
    if opt_idx >= len(options):
        return
        
    option = options[opt_idx]

    for action in option.get('actions', []):
        try:
            exec(action, {"state": state, "quest_data": quest_data})
        except Exception as e:
            print(f"Error executing action '{action}': {e}")

    for logic_block in option.get('logic', []):
        matched = False
        if 'condition' in logic_block:
            try:
                if eval(logic_block['condition'], {"state": state}):
                    matched = True
            except Exception as e:
                print(f"Error evaluating condition '{logic_block['condition']}': {e}")
                continue
        elif 'chance' in logic_block:
            if random.random() <= logic_block['chance']:
                matched = True
        elif logic_block.get('default'):
            matched = True
            
        if matched:
            if 'message' in logic_block:
                msg = bot.send_message(chat_id, logic_block['message'])
                track_cleanup(chat_id, msg.message_id)
                
            if 'ending' in logic_block:
                trigger_ending(chat_id, logic_block['ending'], logic_block.get('sticker'))
                return
                
            if 'next' in logic_block:
                state['scene'] = logic_block['next']
                if logic_block['next'] == 'epilogue' and 'sticker' in logic_block:
                    try:
                        msg = bot.send_sticker(chat_id, logic_block['sticker'])
                        track_cleanup(chat_id, msg.message_id)
                    except telebot.apihelper.ApiTelegramException:
                        msg = bot.send_message(chat_id, f"[Sticker placeholder: {logic_block['sticker']}]")
                        track_cleanup(chat_id, msg.message_id)
                send_scene(chat_id)
                return

if __name__ == '__main__':
    print("Setting up bot commands...")
    bot.set_my_commands([
        telebot.types.BotCommand("/start", "Start or restart current quest"),
        telebot.types.BotCommand("/choose", "Choose a different quest"),
        telebot.types.BotCommand("/endings", "Check unlocked endings")
    ])
    print("Engine is running and ready...")
    bot.infinity_polling()
