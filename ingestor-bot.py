import discord
from discord import app_commands
import json
from fuzzywuzzy import fuzz
from pathlib import Path
from logger import create_logger
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logger
script_name = Path(__file__).stem
logger = create_logger(script_name, log_file=os.getenv("LOG_FILE"))

# Define paths to JSON files using environment variables
NUTRIENT_FILE = Path(os.getenv("NUTRIENT_FILE"))
EFFECT_FILE = Path(os.getenv("EFFECT_FILE"))

# Load JSON data
def load_json_data():
    with open(NUTRIENT_FILE, 'r') as f:
        nutrient_data = json.load(f)
    with open(EFFECT_FILE, 'r') as f:
        effect_data = json.load(f)
    return nutrient_data, effect_data

# Parse effect_value string into an integer
def parse_effect_value(value_str):
    # Remove '%' and optional '+' sign, handle commas
    cleaned = value_str.replace('%', '').replace('+', '').replace(',', '')
    return int(cleaned)

# Initialize Discord client with intents
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

# Fuzzy match threshold and response limit
MATCH_THRESHOLD = 80
MAX_RESPONSE_LENGTH = 1900

# Helper function to format an item (removed 'Value' line)
def format_item(item, source):
    return (
        f"**{source}: {item['key']}**\n"
        f"- Nutrient: {item['nutrient']}\n"
        f"- Duration: {item['duration']}\n"
        f"- Effect: {item['effect']}\n"
    )

def effect_value_from_effect(s):
    return s.split(' ')[0]

# Command handler logic
async def handle_buff_command(interaction, text, sort_key, reverse=True, alpha_sort=False):
    # Load data
    nutrient_data, effect_data = load_json_data()

    # Normalize search text
    search_text = text.lower().strip()

    # Track seen items and collect matches
    seen_keys = set()
    matches = []

    # Search in nutrient-data.json
    for key, details in nutrient_data.items():
        key_lower = key.lower()
        if (search_text.lower() in key_lower) or (fuzz.ratio(search_text, key_lower) >= MATCH_THRESHOLD):
            if key not in seen_keys:
                effect_value = effect_value_from_effect(details['effect'])
                matches.append({
                    'key': key,
                    'nutrient': details['nutrient'],
                    'duration': details['duration'],
                    'effect': details['effect'],
                    'effect_value': effect_value,
                    'parsed_value': parse_effect_value(effect_value),
                    'source': 'Nutrient'
                })
                seen_keys.add(key)

    # Search in effect-data.json
    for key, nutrient_list in effect_data.items():
        key_lower = key.lower()
        if (search_text.lower() in key_lower) or (fuzz.ratio(search_text, key_lower) >= MATCH_THRESHOLD):
            if key not in seen_keys:
                for item in nutrient_list:
                    nutrient_key = item['nutrient'].lower()
                    if nutrient_key not in seen_keys:
                        try:
                            effect_value = effect_value_from_effect(item['effect'])
                            matches.append({
                                'key': key,
                                'nutrient': item['nutrient'],
                                'duration': item['duration'],
                                'effect': item['effect'],
                                'effect_value': effect_value,
                                'parsed_value': parse_effect_value(effect_value),
                                'source': 'Effect'
                            })
                            seen_keys.add(nutrient_key)
                        except Exception as e:
                            logger.error(f"Exception: {e} key={key} item={item}")
                            continue

    # Sort matches
    if alpha_sort:
        matches.sort(key=lambda x: x['key'].lower())
    else:
        matches.sort(key=lambda x: x[sort_key], reverse=reverse)

    # Build response
    buff_command = "/buff"
    if not reverse:
        buff_command += "neg"
    if alpha_sort:
        buff_command += "a"
    buff_command += f" {text}"
    response = f"__Command__: **{buff_command}**   / Data courtesy of **BomberBoi** and __nomansskyresources.com__ /\n"
    items_added = 0
    total_items = len(matches)

    for match in matches:
        source = match['source'] if alpha_sort else match['source']
        item_text = format_item(match, source)
        if len(response) + len(item_text) <= MAX_RESPONSE_LENGTH:
            response += item_text
            items_added += 1
        else:
            break

    # Add summary if not all items were shown
    if items_added < total_items:
        response += f"\n{items_added} out of {total_items} items shown"

    # Log command execution
    logger.info(f"User {interaction.user.name} executed: {buff_command}, Entries found: {total_items}")

    # Send response
    use_ephemeral = (items_added > 6)
    if items_added > 0:
        await interaction.response.send_message(response, ephemeral=use_ephemeral)
    else:
        await interaction.response.send_message(
            f"No matches found for '{text}'. Try adjusting your search term.", ephemeral=True
        )

# Default /buff command (descending order by effect_value)
@tree.command(name="buff", description="Look up NMS buffs, sorted by effect value (descending)")
@app_commands.describe(text="The nutrient or effect to search for")
async def buff_command(interaction: discord.Interaction, text: str):
    logger.debug(f"Executing /buff with text: {text}")
    if interaction.channel_id != 1376435614702112899:
        await interaction.response.send_message("Please use the <#1376435614702112899> channel for this command.", ephemeral=True)
        logger.info(f"User {interaction.user.name} attempted /buff in wrong channel: {interaction.channel_id}")
        return
    await handle_buff_command(interaction, text, 'parsed_value', reverse=True)

# /buffneg command (ascending order by effect_value)
@tree.command(name="buffneg", description="Look up NMS buffs, sorted by effect value (ascending)")
@app_commands.describe(text="The nutrient or effect to search for")
async def buffneg_command(interaction: discord.Interaction, text: str):
    logger.debug(f"Executing /buffneg with text: {text}")
    if interaction.channel_id != 1376435614702112899:
        await interaction.response.send_message("Please use the <#1376435614702112899> channel for this command.", ephemeral=True)
        logger.info(f"User {interaction.user.name} attempted /buffneg in wrong channel: {interaction.channel_id}")
        return
    await handle_buff_command(interaction, text, 'parsed_value', reverse=False)

# /buffa command (alphabetical order by key)
@tree.command(name="buffa", description="Look up NMS buffs, sorted alphabetically by name")
@app_commands.describe(text="The nutrient or effect to search for")
async def buffa_command(interaction: discord.Interaction, text: str):
    logger.debug(f"Executing /buffa with text: {text}")
    if interaction.channel_id != 1376435614702112899:
        await interaction.response.send_message("Please use the <#1376435614702112899> channel for this command.", ephemeral=True)
        logger.info(f"User {interaction.user.name} attempted /buffa in wrong channel: {interaction.channel_id}")
        return
    await handle_buff_command(interaction, text, 'key', alpha_sort=True)

# /buffhelp command (help text, ephemeral)
@tree.command(name="buffhelp", description="Show help for NMS buff bot commands")
async def buffhelp_command(interaction: discord.Interaction):
    help_text = (
        "**NMS Buff Bot Commands**\n"
        "Here's how to use me to find nutrient and effect data from No Man's Sky:\n\n"
        "**/buff <text>** - Search for nutrients or effects matching `<text>`. Results are sorted by effect value (highest to lowest). Supports partial matches (e.g., 'iron' for 'Iron Root').\n"
        "**/buffneg <text>** - Same as /buff, but sorts by effect value from lowest to highest (good for finding negative effects).\n"
        "**/buffa <text>** - Same as /buff, but sorts alphabetically by name and labels items as 'Nutrient' or 'Effect'.\n"
        "**/buffhelp** - Shows this help message (private to you).\n\n"
        "All commands show up to 1900 characters of results. If there's more, you'll see 'N out of M items shown'. Data courtesy of **BomberBoi**!\n"
        "Note: Commands other than `/buffhelp` must be used in the <#1376435614702112899> channel."
    )
    await interaction.response.send_message(help_text, ephemeral=True)
    logger.info("Command executed: /buffhelp, Entries found: 0")

# Sync commands when bot is ready
@client.event
async def on_ready():
    logger.info(f"Logged in as {client.user}")
    await tree.sync()
    logger.info("Commands synced")

# Handle direct messages and mentions
@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # Check if it's a direct message
    is_dm = isinstance(message.channel, discord.DMChannel)
    
    # Check if the bot is mentioned in the message
    is_mentioned = client.user.mentioned_in(message)
    
    if not is_dm and not is_mentioned:
        return

    # Remove bot mention if present
    content = message.content.replace(f"<@{client.user.id}>", "").strip()
    
    # Define known commands
    known_commands = {
        "buff": buff_command,
        "buffneg": buffneg_command,
        "buffa": buffa_command,
        "buffhelp": buffhelp_command
    }
    
    # Parse the command and argument
    parts = content.split(" ", 1)
    if not parts:
        return
        
    command_name = parts[0].lower()
    argument = parts[1] if len(parts) > 1 else ""
    
    if command_name not in known_commands:
        if is_dm:
            await message.channel.send("Unknown command. Available commands are: buff, buffneg, buffa, buffhelp.")
        return
    
    # Log the command execution
    logger.info(f"User {message.author.name} executed via {'DM' if is_dm else 'mention'}: {command_name} {argument}")
    
    # Create a mock interaction for command execution
    class MockInteraction:
        def __init__(self, message):
            self.user = message.author
            self.channel_id = message.channel.id
            self.response = self.Response(message.channel)
            
        class Response:
            def __init__(self, channel):
                self.channel = channel
                
            async def send_message(self, content, ephemeral=False):
                if ephemeral and isinstance(self.channel, discord.DMChannel):
                    await self.channel.send(content)
                elif ephemeral:
                    await self.channel.send(content + "\n*(This message is only visible to you)*")
                else:
                    await self.channel.send(content)
    
    mock_interaction = MockInteraction(message)
    
    # Execute the command
    command_func = known_commands[command_name]
    if command_name == "buffhelp":
        await command_func(mock_interaction)
    else:
        if mock_interaction.channel_id != 1376435614702112899 and not is_dm:
            await mock_interaction.response.send_message("Please use the <#1376435614702112899> channel for this command.", ephemeral=True)
            logger.info(f"User {message.author.name} attempted {command_name} in wrong channel: {mock_interaction.channel_id}")
            return
        await command_func(mock_interaction, argument)

# Run the bot using environment variable
client.run(os.getenv("DISCORD_TOKEN"))
