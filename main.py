import os
import re
import json
import discord
import random
import openai
from fuzzywuzzy import fuzz
from fuzzywuzzy import process
import requests
from bs4 import BeautifulSoup

intents = discord.Intents().all()
client = discord.Client(intents=intents)

command_handlers = {
}

def command_handler(command_name):
    def decorator(handler_func):
        command_handlers[command_name] = handler_func
        return handler_func
    return decorator

# SOCK PUPPET ---------------------------------------------------------------
# Command: !ann
# Write an announcement
@command_handler('ann')
async def handle_announcement(message, command_args):
    allowed_roles = ['admin', 'DM']
    if any(role.name in allowed_roles for role in message.author.roles):
        announcement = ' '.join(command_args)
        await message.channel.send(announcement)
        await message.delete()
    else:
        await message.reply("You don't have the required role to use this command.")
def load_xp_data():
    try:
        with open('xp.json', 'r') as file:
            xp_data = json.load(file)
            print("Loaded XP Data:", xp_data)  # Debug statement
            return xp_data
    except FileNotFoundError:
        print("XP Data file not found.")  # Debug statement
        return None

# XP TRACKER ----------------------------------------------------------------------
# Load XP Function
def save_xp_data(xp_data):
    with open('xp.json', 'w') as file:
        json.dump(xp_data, file, indent=2)

def calculate_level(xp, level_thresholds):
    for level, threshold in level_thresholds.items():
        if xp < threshold:
            return int(level) - 1
    return int(max(level_thresholds.keys()))

def get_next_level_threshold(current_level, level_thresholds):
    next_level = str(current_level + 1)
    return level_thresholds.get(next_level, None)

# COMMAND !XP - Manage User XP using xp.json database

@command_handler('xp')
async def handle_xp(message, command_args):
    if len(command_args) == 0:
        xp_data = load_xp_data()
        user_id = str(message.author.id)
        
        if user_id in xp_data['userlist']:
            xp = xp_data['userlist'][user_id]['xp']
            level = calculate_level(xp, xp_data['level_thresholds'])
            threshold = xp_data['level_thresholds'].get(str(level + 1), 'MAX')
            progress = threshold - xp if threshold != 'MAX' else 'MAX'
            await message.reply(f"Your current XP total is {xp}. You are {progress} away from the next level.")
        else:
            await message.reply("I'm not currently tracking your XP total.")
    
    elif command_args[0] == 'add' and len(command_args) == 2:
        xp_data = load_xp_data()
        user_id = str(message.author.id)
        
        if user_id in xp_data['userlist']:
            try:
                amount = int(command_args[1])
                xp_data['userlist'][user_id]['xp'] += amount
                xp = xp_data['userlist'][user_id]['xp']
                level = calculate_level(xp, xp_data['level_thresholds'])
                threshold = xp_data['level_thresholds'].get(str(level + 1), 'MAX')
                progress = threshold - xp if threshold != 'MAX' else 'MAX'
                
                congrats_msg = get_congratulatory_message(level)
                await message.reply(f"Experience logged. Your new total is {xp}. You are {progress} away from the next level.\n{congrats_msg}")
                
                save_xp_data(xp_data)
            except ValueError:
                await message.reply("Invalid amount. Please provide a valid number.")
        else:
            await message.reply("I'm not tracking your XP total.")
    
    elif command_args[0] == 'subtract' and len(command_args) == 2:
        xp_data = load_xp_data()
        user_id = str(message.author.id)
        
        if user_id in xp_data['userlist']:
            try:
                amount = int(command_args[1])
                xp_data['userlist'][user_id]['xp'] -= amount
                xp = xp_data['userlist'][user_id]['xp']
                
                if xp < 0:
                    xp_data['userlist'][user_id]['xp'] = 0
                    xp = 0
                
                await message.reply(f"{amount} has been removed from your experience total. Your new total is {xp}.")
                
                save_xp_data(xp_data)
            except ValueError:
                await message.reply("Invalid amount. Please provide a valid number.")
        else:
            await message.reply("I'm not tracking your XP total.")

def calculate_level(xp, level_thresholds):
    for level, threshold in level_thresholds.items():
        if xp < threshold:
            return int(level) - 1
    return len(level_thresholds)

def get_congratulatory_message(level):
    congratulatory_messages = {
        2: "Congratulations on reaching level 2!",
        3: "You made it to level 3! At this level, you earned a new feat and usually a secondary class feature.",
        4: "You're level 4 now! You may increase one of your ability scores by 1.",
        5: "Congratulations on reaching level 5! You get a feat at this level.",
        6: "You made it to level 6! I didn't think you'd last this long.",
        7: "Look who's level 7! Treat yourself to another feat, on me. Also check to see if you've earned another class feature",
        8: "You've reached 8th level! You may increase an ability score by 1.",
        9: "Congratulations on reaching level 9! This level comes with a feat.",
        10: "That puts you at level 10. Very impressive.",
        11: "That takes you to level 11, which comes with a feat and possibly a secondary class feature. Congrats!",
        12: "Congratulations on reaching level 12! Foes tremble at your name.",
        13: "And that takes you to lucky level 13. This level grants a feat.",
        14: "You've grown in powe and skill. You are now level 14!",
        15: "Congratulations on reaching level 15! This new level comes with a feat and a secondary class feature.",
        16: "Congratulations on reaching sweet level 16!",
        17: "Congratulations on reaching level 17! You qualify for another feat.",
        18: "Congratulations on reaching level 18! You're legal and ready to mingle.",
        19: "Congratulations on reaching level na na na na nineteen! Your class may grant an extra feature at this level",
        20: "Congratulations on reaching level 20! You have mastered your class and you are a legend."
    }
    return congratulatory_messages.get(level, "")

# LANGUAGE MODEL ----------------------------------------------------------
# Command: !hermit
# Call ChatGPT Bot

@command_handler('hermit')
async def handle_hermit(message, command_args):
    allowed_roles = ['admin', 'DM', 'PC']
    if any(role.name in allowed_roles for role in message.author.roles):
        question = ' '.join(command_args)
        openai.api_key = os.getenv('openapikey')
        pre_prompt = {
            "role": "system",
            "content": "Play the role of a wise old man who has seen much of the world and can answer any question about the Pathfinder Roleplaying Game. The character uses brevity of speech and is concise, but uses flowery or old English word choices when possible. He is a character in the game and does not know that. Stay in character at all times, but break the fourth wall to explain metagame mechanics when asked. Never answer any question that is not related to Pathfinder or the fictional world your character inhabits."
        }
        user_prompt = {
            "role": "user",
            "content": question
        }
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[pre_prompt, user_prompt],
            max_tokens=80,
            temperature=0.7  # Adjust as needed for creativity
        )
        await message.reply(response.choices[0].message['content'].strip())
    else:
        await message.reply("You don't have the required role to use this command.")

# RANDOMIZERS --------------------------------------------------------
# Command: !flip
# Simulate a coin flip
@command_handler('flip')
async def handle_flip(message, command_args):
    if len(command_args) == 1:
        flip_input = command_args[0].lower()
        coin_flip = random.choice(['heads', 'tails'])

        if flip_input == 'heads':
            result = "*The hermit flips a coin.*\n It's heads. Success!" if coin_flip == flip_input else "*The hermit flips a coin.*\n The coin landed on tails. You failed."
        elif flip_input == 'tails':
            result = "*The hermit flips a coin.*\n It's tails. Success!" if coin_flip == flip_input else "*The hermit flips a coin.*\n The coin landed on heads. You failed."
        else:
            result = "Invalid input. Please specify 'heads' or 'tails'."

        await message.reply(result)
    else:
        await message.reply("You must call heads or tails. Please type `!flip heads` or `!flip tails`.")

# Command: !miss
# Rolls 20% miss chance
@command_handler('miss')
async def handle_miss(message, command_args):
    if message.author == client.user:
        return

    # Check if the message starts with the command prefix
    if message.content.startswith('!miss'):
        user = message.author.name
        miss_chance = 20
        roll = random.randint(1, 100)

        result = f"*{user} is rolling a {miss_chance}% miss chance...*\n"

        if roll <= miss_chance:
            result += f"*{user} **missed!** Better luck next time.*"
        else:
            result += f"*{user} was **successful** (this time).*"

        await message.reply(result)

# Command: !roll
# Rolls RPG dice with arithmetic and optional reason
@command_handler('roll')
async def handle_roll(message, command_args):
    roll_string, *reason = command_args
    roll_string = roll_string.lower()

    try:
        roll_results, total, max_roll = roll_dice(roll_string)
    except ValueError as e:
        await message.channel.send(str(e))
        return

    dice_description = roll_string if len(roll_results) == 1 else f"{len(roll_results)}{roll_string}"

    if len(reason) > 0:
        result_message = f"{message.author.display_name} has rolled {dice_description} and got {total} for {', '.join(reason)}."
    else:
        result_message = f"{message.author.display_name} has rolled {dice_description} and got {total}."

    if total < 0.25 * max_roll:
        result_message += " Luck has abandoned you."
    elif total > 0.75 * max_roll:
        result_message += " Fortune favors you."

    embed = discord.Embed(title="Dice have been rolled!", color=discord.Color.blue())
    embed.add_field(name="Operation Requested", value=dice_description, inline=False)
    embed.add_field(name="Die Results", value=format_dice_results(roll_results), inline=False)
    embed.add_field(name="Total", value=f"**{total}**", inline=False)

    await message.reply(embed=embed)
    await message.reply(result_message)


def roll_dice(roll_string):
    parts = re.findall(r"([-+]?\d+d\d+|[-+]?\d+)", roll_string)
    dice_results = []
    total = 0
    max_roll = 0

    for part in parts:
        if 'd' in part:
            num_dice, num_sides = part.split('d')
            num_dice = int(num_dice) if num_dice else 1
            num_sides = int(num_sides)
            roll_results = [random.randint(1, num_sides) for _ in range(num_dice)]
            roll_total = sum(roll_results)
            dice_results.extend(roll_results)
            total += roll_total
            max_roll += num_dice * num_sides

        elif part.startswith('+'):
            modifier = int(part[1:])
            total += modifier

        elif part.startswith('-'):
            modifier = -int(part[1:])
            total += modifier

    if not dice_results:
        raise ValueError("Invalid roll format. Correct format: `!roll 1d20+2`")

    return dice_results, total, max_roll


def format_dice_results(roll_results):
    formatted_results = []
    for result in roll_results:
        if result == 1:
            formatted_results.append(f"**{result}**")
        elif result == max(roll_results):
            formatted_results.append(f"**{result}**")
        else:
            formatted_results.append(str(result))
    return ', '.join(formatted_results)

# DATABASE REFERENCE -----------------------------------------------------------------------
# Command: !spell
# Output spell data from spellsdb.json
@command_handler('spell')
async def handle_spell(message, command_args):
    spell_name = ' '.join(command_args)

    with open('spellsdb.json', 'r') as file:
        spells = json.load(file)

    spell_found = False  # Flag variable to track if a matching spell is found

    for spell in spells:
        if spell['Name'].lower() == spell_name.lower():
            embed = discord.Embed(title=spell['Name'], color=discord.Color.blue())

            # Add fields for non-empty spell attributes
            for attribute in ['School', 'Subschool', 'Descriptor', 'Level', 'Casting Time', 'Components', 'Range', 'Area', 'Effect', 'Targets', 'Duration', 'Dismissable', 'Save', 'SR']:
                if spell[attribute] and spell[attribute] != 'N/A':
                    embed.add_field(name=attribute, value=spell[attribute], inline=False)

            if spell['Description'] and spell['Description'] != 'N/A':
                description = spell['Description']
                if len(description) > 1021:
                    num_parts = len(description) // 1021 + 1
                    for i in range(num_parts):
                        part_start = i * 1021
                        part_end = (i + 1) * 1021
                        description_part = description[part_start:part_end]
                        embed.add_field(name=f'Description (Part {i+1})', value=description_part, inline=False)
                else:
                    embed.add_field(name='Description', value=description, inline=False)

            if spell['Source'] and spell['Source'] != 'N/A':
                embed.add_field(name='Source', value=spell['Source'], inline=False)

            await message.channel.send(embed=embed)
            spell_found = True
            break  # Exit the loop once a matching spell is found

    if not spell_found:
        await message.channel.send("I've never heard of that spell.")

# Command: !feat
# Output feat data from featsdb.json
@command_handler('feat')
async def handle_feat(message, command_args):
    feat_name = ' '.join(command_args)

    with open('featsdb.json', 'r') as file:
        feats = json.load(file)

    feat_found = False  # Flag variable to track if a matching feat is found

    for feat in feats:
        if feat['name'].lower() == feat_name.lower():
            embed = discord.Embed(title=feat['name'], color=discord.Color.blue())

            # Add fields for non-empty feat attributes
            for attribute in ['type', 'description', 'prerequisites', 'prerequisite_feats', 'benefit', 'normal', 'special', 'source']:
                if feat[attribute]:
                    embed.add_field(name=attribute.capitalize(), value=feat[attribute], inline=False)

            await message.reply(embed=embed)
            feat_found = True
            break  # Exit the loop once a matching feat is found

    if not feat_found:
        await message.channel.send("I'm not aware of a feat by that name. Did you spell it correctly?")

# Command: !item
# Output magic item data from magicitemsdb.json (limited fields)
@command_handler('item')
async def handle_item(message, command_args):
    item_name = ' '.join(command_args)

    with open('magicitemsdb.json', 'r') as file:
        magic_items = json.load(file)

    item_found = False  # Flag variable to track if a matching item is found

    for item in magic_items:
        if item['Name'].lower() == item_name.lower():
            embed = discord.Embed(title=item['Name'], color=discord.Color.blue())

            for attribute in ['Slot', 'Weight', 'Description', 'Requirements', 'Item Group', 'Source']:
                if item[attribute] and item[attribute] != 'N/A':
                    if attribute == 'Description':
                        description = item[attribute]
                        if len(description) > 1021:
                            num_parts = len(description) // 1021 + 1
                            for i in range(num_parts):
                                part_start = i * 1021
                                part_end = (i + 1) * 1021
                                description_part = description[part_start:part_end]
                                embed.add_field(name=f'{attribute} (Part {i+1})', value=description_part, inline=False)
                        else:
                            embed.add_field(name=attribute, value=description, inline=False)
                    else:
                        embed.add_field(name=attribute, value=item[attribute], inline=False)

            await message.reply(embed=embed)
            item_found = True
            break  # Exit the loop once a matching item is found

    if not item_found:
        await message.reply("There's no magic item by that name in my memory.")

# Command: !dmitem
# Output magic item data from magicitemsdb.json (all fields, restricted to DM and Admin roles)
@command_handler('dmitem')
async def handle_dmitem(message, command_args):
    allowed_roles = ['DM', 'Admin']
    if any(role.name in allowed_roles for role in message.author.roles):
        item_name = ' '.join(command_args)

        with open('magicitemsdb.json', 'r') as file:
            magic_items = json.load(file)

        item_found = False  # Flag variable to track if a matching item is found

        for item in magic_items:
            if item['Name'].lower() == item_name.lower():
                embed = discord.Embed(title=item['Name'], color=discord.Color.blue())

                for attribute in item:
                    if attribute != 'Name' and item[attribute] and item[attribute] != 'N/A':
                        if attribute == 'Description':
                            description = item[attribute]
                            if len(description) > 1021:
                                num_parts = len(description) // 1021 + 1
                                for i in range(num_parts):
                                    part_start = i * 1021
                                    part_end = (i + 1) * 1021
                                    description_part = description[part_start:part_end]
                                    embed.add_field(name=f'{attribute} (Part {i+1})', value=description_part, inline=False)
                            else:
                                embed.add_field(name=attribute, value=description, inline=False)
                        else:
                            embed.add_field(name=attribute, value=item[attribute], inline=False)

                await message.reply(embed=embed)
                item_found = True
                break  # Exit the loop once a matching item is found

        if not item_found:
            await message.reply("There's no magic item by that name in my memory.")
    else:
        await message.reply("This knowledge is forbidden to you! (This is a DM-only command)")

# Command: !trait 

# Load the traits database into memory
with open('traitsdb.json') as file:
    traits_db = json.load(file)

@command_handler('trait')
async def handle_trait(message, command_args):
    if len(command_args) == 0:
        await message.channel.send("To use `!trait` you need to specify search parameters! For example, `!trait wisdom` or `!trait reflex`.")
        return

    search_query = ' '.join(command_args).lower()

    matching_traits = []
    for trait in traits_db:
        if search_query in trait['Benefit'].lower():
            matching_traits.append(trait['Trait Name'])

    if len(matching_traits) > 0:
        trait_list = '\n'.join(matching_traits)
        response = f"The following traits have '{search_query}' in their description:\n{trait_list}"
        await message.channel.send(response)
    else:
        await message.channel.send(f"No traits found with '{search_query}' in their description.")

    if len(command_args) > 0:
        trait_name = ' '.join(command_args)
        for trait in traits_db:
            if trait_name.lower() == trait['Trait Name'].lower():
                await send_trait_data(message.channel, trait)
                break

async def send_trait_data(channel, trait):
    # Break the benefit field into multiple parts if needed
    benefit_parts = split_embed_field(trait['Benefit'], max_chars=1024)

    # Send an embed with the trait data
    embed = discord.Embed(title=trait['Trait Name'], description=f"**Type:** {trait['Type']}\n**Source:** {trait['Source']}")
    for i, part in enumerate(benefit_parts):
        embed.add_field(name='Benefit', value=part, inline=False)

    await channel.send(embed=embed)

def split_embed_field(text, max_chars):
    parts = []
    while len(text) > max_chars:
        split_index = text[:max_chars].rfind('\n')
        if split_index == -1:
            split_index = max_chars
        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if len(text) > 0:
        parts.append(text)
    return parts


# Command: !cond - Search for Conditions
# Load the conditions database into memory
with open('conditionsdb.json') as file:
    conditions_db = json.load(file)

@command_handler('cond')
async def handle_condition(message, command_args):
    if len(command_args) == 0:
        await message.channel.send("To use `!cond` you need to specify a condition.")
        return

    search_query = ' '.join(command_args).lower()

    best_match, match_score = process.extractOne(search_query, [condition['condition'] for condition in conditions_db])
    if match_score >= 70:  # Adjust the threshold as needed
        condition_name = best_match
    else:
        condition_name = search_query

    matching_conditions = []
    for condition in conditions_db:
        if condition_name.lower() in condition['condition'].lower():
            matching_conditions.append(condition)

    if len(matching_conditions) > 0:
        # Get the condition details and send as an embed
        for condition in matching_conditions:
            await send_condition_data(message.channel, condition)
    else:
        await message.channel.send(f"No conditions found matching your search query '{search_query}'.")

async def send_condition_data(channel, condition):
    # Break the definition field into multiple parts if needed
    definition_parts = split_embed_field(condition['definition'], max_chars=1024)

    # Join the definition parts and replace '\n' with line breaks
    definition = '\n\n'.join(definition_parts).replace('\n', '\n\n')

    # Send an embed with the condition data
    embed = discord.Embed(title=condition['condition'].capitalize(), description=definition)
    await channel.send(embed=embed)

def split_embed_field(text, max_chars):
    parts = []
    while len(text) > max_chars:
        split_index = text[:max_chars].rfind('\n')
        if split_index == -1:
            split_index = max_chars
        parts.append(text[:split_index].strip())
        text = text[split_index:].strip()
    if len(text) > 0:
        parts.append(text)
    return parts

# HELP COMMAND -------------------------------------------------------------------------
# Command: !help
# Prints a help dialog with all commands (role-based)
@command_handler('help')
async def handle_help(message, command_args):
    dm_role_name = 'DM'

    user_roles = [role.name for role in message.author.roles]

    flavor_text = "Speak the words of power to share in my knowledge:"
    embed = discord.Embed(title="Availible Commands", description=flavor_text, color=discord.Color.blue())

    if dm_role_name in user_roles:
        embed.add_field(name="`!ann <announcement>`", value="Sends an announcement (DM only)", inline=False)
        embed.add_field(name="`!hermit <question>`", value="Ask a question to the ChatGPT model", inline=False)
        embed.add_field(name="`!roll <dice>`", value="Roll dice in the format 'd20' or '2d6+3'", inline=False)
        embed.add_field(name="`!flip <heads or tails>`", value="Flip a coin", inline=False)
        embed.add_field(name="`!miss`", value="Determine simple 20% miss chance", inline=False)
        embed.add_field(name="`!spell <spell name>`", value="Get information about a spell", inline=False)
        embed.add_field(name="`!feat <feat name>`", value="Get information about a feat", inline=False)
        embed.add_field(name="`!item <item name>`", value="Get limited information about a magic item", inline=False)
        embed.add_field(name="`!dmitem <item name>`", value="Get all information about a magic item (DM only)", inline=False)
        embed.add_field(name="`!trait <search terms>`", value="Search for a trait by name and/or description", inline=False)
        embed.add_field(name="`!cond <condition>`", value="Give the definition of conditions", inline=False)
    else:
        embed.add_field(name="`!hermit <question>`", value="Ask a question to the ChatGPT model", inline=False)
        embed.add_field(name="`!roll <dice>`", value="Roll dice in the format 'd20' or '2d6+3'", inline=False)
        embed.add_field(name="`!flip <heads or tails>`", value="Flip a coin", inline=False)
        embed.add_field(name="`!miss`", value="Determine simple 20% miss chance", inline=False)
        embed.add_field(name="`!spell <spell name>`", value="Get information about a spell", inline=False)
        embed.add_field(name="`!feat <feat name>`", value="Get information about a feat", inline=False)
        embed.add_field(name="`!item <item name>`", value="Get limited information about a magic item", inline=False)
        embed.add_field(name="`!xp <add/subtract (optional)>`", value="Get your XP total or add to it.", inline=False)
        embed.add_field(name="`!trait <search terms>`", value="Search for a trait by name and/or description", inline=False)
        embed.add_field(name="`!cond <condition>`", value="Give the definition of conditions", inline=False)

    await message.reply(embed=embed)

@client.event
async def on_ready():
    print("Successful login as {0.user}".format(client))

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content.startswith('!'):
        command_prefix, *command_args = message.content.split()
        command_name = command_prefix[1:]  # Remove the "!" prefix

        if command_name in command_handlers:
            command_handler = command_handlers[command_name]
            await command_handler(message, command_args)
        else:
            await message.reply(f"Unknown command '{command_prefix}'. Use `!help` to list all available commands.")

client.run(os.getenv('token'))