# JSON Text Quest Engine

A lightweight, fully data-driven text quest engine for Telegram and the command line.

The engine (`telegram_bot.py` and `console_bot.py`) does not contain any hardcoded game logic. Everything—including scenes, variables, state mutations, transition logic, random events, and endings—is entirely configured via JSON files.

## Features
- **JSON-Driven Logic**: Define all game mechanics inside JSON without writing a single line of Python code.
- **Dynamic Text**: Texts and button labels can change dynamically depending on the player's variables (e.g. show different text if `health < 50`).
- **State Management**: Evaluate mathematical expressions and run Python logic under the hood to update inventory, counters, or flags.
- **Probabilities & Randomness**: Native support for chance-based events (e.g. 30% chance to fail an action).
- **Multiple Quests Support**: The engine automatically scans the `quests/` directory. If multiple quests are found, it creates an interactive menu for the player to choose from.
- **Ending Tracker**: Automatically tracks and counts unlocked endings for each player.
- **Two Interfaces**: Play directly in the terminal or deploy as a Telegram bot.
- **Docker Ready**: Easy to deploy with the included Dockerfile.

## Getting Started

### 1. Playing in the Console
You can play the quests locally in your terminal without any setup:
```bash
python3 console_bot.py
```

### 2. Running the Telegram Bot
To run the Telegram bot, you will need a bot token from [@BotFather](https://t.me/BotFather).

1. Copy the environment file template:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and insert your bot token:

3. Build the Docker image:
   ```bash
   docker build -t json-quest-engine .
   ```
4. Run the container:
   ```bash
   docker run -d --name quest_bot --env-file .env json-quest-engine
   ```

## Creating Your Own Quest

To create a new quest, simply add a new `.json` file to the `quests/` directory. Check out `quests/example_quest.json.example` for a highly readable, annotated example.

### JSON Syntax Guide

A quest JSON requires a few top-level keys:
- `title`: The name of the quest (used in menus).
- `total_endings`: The total number of endings (used for the progress tracker).
- `initial_message`: A welcome message printed when the quest is selected.
- `initial_state`: A dictionary of starting variables (e.g., `{"gold": 0, "health": 100, "scene": "start"}`).
- `scenes`: A dictionary containing all the scenes.

#### Scenes
Every scene must have a `text` and a list of `options`.

**Dynamic Text:**
Text can be a simple string, or a list of conditional blocks. The engine evaluates them from top to bottom and uses the first one that matches:
```json
"text": [
  {"condition": "state['gold'] > 10", "value": "You feel rich."},
  {"default": true, "value": "You are poor."}
]
```
*Note: This conditional structure can be used for scene text AND button option texts.*

#### Options
Every option inside a scene can contain three components: `text`, `actions`, and `logic`.

**1. `text`:** What the button says (can be conditional, as shown above).

**2. `actions`:** (Optional) A list of Python string expressions to execute *immediately* when the user clicks the button, before evaluating where to go next. Useful for modifying variables.
```json
"actions": [
  "state['gold'] -= 5",
  "state['has_key'] = True"
]
```

**3. `logic`:** A list of rules that determines what happens next. The engine checks them from top to bottom.
- `condition`: A Python expression (e.g. `"state['health'] > 0"`). If true, this logic block triggers.
- `chance`: A float between 0.0 and 1.0 (e.g. `0.33` for 33%). If the random roll succeeds, this logic block triggers.
- `default`: Set to `true` as a fallback.

**When a logic block triggers, it can specify:**
- `next`: The ID of the next scene to load.
- `ending`: The text of an ending. This will end the game and update the player's ending tracker.
- `message`: A pop-up notification / intermediate message to show before proceeding.
- `sticker`: (Telegram only) A Telegram file ID to send a sticker.

Example of a complex option:
```json
"options": [
  {
    "text": "Try to pick the lock",
    "actions": ["import random", "state['roll'] = random.random()"],
    "logic": [
      {
        "condition": "state['roll'] < 0.3",
        "message": "The lockpick breaks!",
        "next": "jail_scene"
      },
      {
        "default": true,
        "message": "Click! The door opens.",
        "next": "treasure_room"
      }
    ]
  }
]
```

## Repository Structure
- `quests/` — Place all your `.json` quests here.
- `telegram_bot.py` — The Telegram interpreter engine.
- `console_bot.py` — The command-line interpreter engine.
- `quests/example_quest.json.example` — A complete tutorial quest demonstrating variables, randomness, and conditions.

## License
MIT License
