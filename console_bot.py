import json
import random
import glob
import os

loaded_quests = {}
quest_files = glob.glob('quests/*.json')
for file_path in quest_files:
    if file_path.endswith('.example'):
        continue
    quest_id = os.path.splitext(os.path.basename(file_path))[0]
    with open(file_path, 'r', encoding='utf-8') as f:
        loaded_quests[quest_id] = json.load(f)

if not loaded_quests:
    print("Error: No quests loaded in quests/ directory")
    exit(1)

def eval_text(text_block, current_state):
    """Evaluates which text to show based on JSON conditions."""
    if isinstance(text_block, str):
        return text_block
    if isinstance(text_block, list):
        for item in text_block:
            condition = item.get('condition')
            if condition:
                try:
                    if eval(condition, {"state": current_state}):
                        return item.get('value', '')
                except Exception as e:
                    print(f"Error evaluating condition '{condition}': {e}")
                    continue
            if item.get('default'):
                return item.get('value', '')
    return ""

def play_console():
    if len(loaded_quests) == 1:
        quest_id = list(loaded_quests.keys())[0]
        print(f"Loaded quest: {loaded_quests[quest_id].get('title', quest_id)}")
    else:
        print("\nAvailable quests:")
        quests_list = list(loaded_quests.items())
        for idx, (q_id, q_data) in enumerate(quests_list):
            title = q_data.get('title', q_id)
            print(f"[{idx + 1}] {title}")
            
        while True:
            try:
                choice = int(input("\nChoose a quest (number): ")) - 1
                if 0 <= choice < len(quests_list):
                    quest_id = quests_list[choice][0]
                    break
                print("Quest not found!")
            except ValueError:
                print("Please enter a number!")

    quest_data = loaded_quests[quest_id]
    state = dict(quest_data.get('initial_state', {}))
    unlocked_endings = set()
    
    print("\n" + "="*40)
    print(quest_data.get('initial_message', 'Welcome to the game!'))
    print("="*40)

    while True:
        scene_id = state.get('scene', 'scene_1')
        
        if scene_id not in quest_data['scenes']:
            print("Error: scene not found!")
            break

        scene_info = quest_data['scenes'][scene_id]
        
        print("\n" + "="*40)
        text = eval_text(scene_info.get('text', ''), state)
        print(text)
        print("-" * 40)

        options = scene_info.get('options', [])
        valid_options = []
        
        for idx, opt in enumerate(options):
            btn_text = eval_text(opt.get('text', ''), state)
            if btn_text:
                valid_options.append((idx, opt, btn_text))
                print(f"[{len(valid_options)}] {btn_text}")

        if not valid_options:
            print("\nNo options available. Game over.")
            break

        try:
            choice_num = int(input("\nYour choice (number): ")) - 1
            if choice_num < 0 or choice_num >= len(valid_options):
                print("Invalid choice!")
                continue
        except ValueError:
            print("Please enter a number!")
            continue

        real_idx, option, _ = valid_options[choice_num]

        for action in option.get('actions', []):
            try:
                exec(action, {"state": state, "quest_data": quest_data})
            except Exception as e:
                print(f"Error executing action '{action}': {e}")

        logic_blocks = option.get('logic', [])
        transitioned = False

        for logic_block in logic_blocks:
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
                    print(f"\n>>> {logic_block['message']}")
                    
                if 'ending' in logic_block:
                    ending_text = logic_block['ending']
                    unlocked_endings.add(hash(ending_text))
                    unlocked = len(unlocked_endings)
                    total = quest_data.get('total_endings', 0)
                    print(f"\n💀 {ending_text}")
                    if 'sticker' in logic_block:
                        print(f"[Sticker sent: {logic_block['sticker']}]")
                    if total > 0:
                        print(f"🏆 Endings unlocked: {unlocked}/{total}")
                    print("\n--- GAME OVER ---")
                    
                    ans = input("\nRestart? (y/n): ")
                    if ans.lower() in ['y', 'д', 'yes']:
                        state.clear()
                        state.update(quest_data['initial_state'])
                        transitioned = True
                        break
                    else:
                        return
                    
                if 'next' in logic_block:
                    state['scene'] = logic_block['next']
                    if logic_block['next'] == 'epilogue':
                        epilogue_text = eval_text(quest_data['scenes']['epilogue'].get('text', ''), state)
                        unlocked_endings.add(hash(epilogue_text))
                        unlocked = len(unlocked_endings)
                        total = quest_data.get('total_endings', 0)
                        if 'sticker' in logic_block:
                            print(f"[Sticker sent: {logic_block['sticker']}]")
                        if total > 0:
                            print(f"🏆 Endings unlocked: {unlocked}/{total}")
                    transitioned = True
                    break

        if not transitioned and logic_blocks:
            print("Warning: No condition matched, transition not executed.")

if __name__ == '__main__':
    play_console()
