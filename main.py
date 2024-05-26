from discord import Intents, Embed
from discord.ext import commands
import random
import asyncio

intents = Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='?', intents=intents)


TOKEN = ""

joined_users = []
game_started = False
imposter = None
description_phase_started = False
user_descriptions = {}

@client.event
async def on_ready():
    print('Bot is ready.')

@client.command()
async def play(ctx):
    global game_started
    if not game_started:
        embed = Embed(title="Game Start", description="React with ✅ if you want to play!", color=0x00ff00)
        message = await ctx.send(embed=embed)
        await message.add_reaction("✅")
    else:
        await ctx.send("The game has already started. You cannot join now.")

@client.event
async def on_raw_reaction_add(payload):
    global game_started
    if not game_started:
        if payload.emoji.name == "✅":
            if payload.member and not payload.member.bot:
                joined_users.append(payload.user_id)
                user = await client.fetch_user(payload.user_id)
                await user.send("You have joined the queue")
    else:
        member = payload.member
        if member:
            await member.send("The game has already started. You cannot join now.")

@client.command()
async def start(ctx):
    global game_started, imposter
    if not game_started:
        if len(joined_users) > 2:
            random_word = generate_random_word('nouns.txt')
            imposter = random.choice(joined_users)
            for user_id in joined_users:
                user = await client.fetch_user(user_id)
                if user_id == imposter:
                    await user.send("You are the imposter!")
                else:
                    await user.send(f"Your random word: {random_word}")
            game_started = True
            await ctx.send("The game has started!")
        else:
            await ctx.send("No users have joined yet.")
    else:
        await ctx.send("The game has already started.")

@client.command()
async def describe(ctx):
    global game_started, description_phase_started, user_descriptions, joined_users
    if game_started and not description_phase_started:
        description_phase_started = True
        await ctx.send("Description phase has started. Users, please describe your words one by one.")
        for round_number in range(2):
            await ctx.send(f"Round {round_number + 1}")
            for user_id in joined_users:
                user = await client.fetch_user(user_id)
                await ctx.send(f"{user.mention}, please describe your word.")
                def check(m):
                    return m.author.id == user_id and m.channel == ctx.channel
                try:
                    description_msg = await client.wait_for('message', check=check, timeout=30)
                    user_descriptions[user_id] = description_msg.content
                    await ctx.send(f"Thank you {user.mention}, your description has been recorded.")
                except asyncio.TimeoutError:
                    await ctx.send(f"{user.mention}, you took too long to respond. Your description was not recorded.")
        await ctx.send("Description phase completed. Commence voting.")
        await start_voting(ctx)
    elif not game_started:
        await ctx.send("The game has not started yet.")
    else:
        await ctx.send("Description phase is already in progress.")

async def start_voting(ctx):
    global joined_users, imposter
    embed = Embed(title="Vote for the Imposter", description="React with the number corresponding to the user you suspect is the imposter.", color=0xff0000)
    for index, user_id in enumerate(joined_users, start=1):
        user = await client.fetch_user(user_id)
        embed.add_field(name=f"{index}. {user.name}", value=user.id, inline=False)
    voting_message = await ctx.send(embed=embed)
    for i in range(1, len(joined_users) + 1):
        await voting_message.add_reaction(str(i) + '️⃣')
        await asyncio.sleep(1)

    def check(reaction, user):
        return user.id in joined_users and str(reaction.emoji)[0].isdigit()   

    try:
        reaction, user = await client.wait_for('reaction_add', check=check, timeout=60)
        voted_user_index = int(str(reaction.emoji)[0]) - 1
        voted_user_id = joined_users[voted_user_index]
        if voted_user_id == imposter:
            await ctx.send(f"Congratulations! You win. The user you suspected ({user.name}) was the imposter!")
        else:
            imposter_user = await client.fetch_user(imposter)
            await ctx.send(f"Sorry, you lose. The imposter was {imposter_user.name}.")
        await ask_replay(ctx)
    except asyncio.TimeoutError:
        await ctx.send("Voting time has expired.")

async def ask_replay(ctx):
    global game_started, joined_users, imposter, description_phase_started, user_descriptions
    embed = Embed(title="Play Again?", description="React with ✅ to play again or ❌ to end the game.", color=0x00ff00)
    message = await ctx.send(embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, user):
        return user.id in joined_users and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await client.wait_for('reaction_add', check=check, timeout=60)
        if str(reaction.emoji) == "✅":
            await ctx.send("Starting a new game!")
            reset_game()
            await play(ctx)
        else:
            await ctx.send("Ending the game. Thanks for playing!")
            reset_game()
    except asyncio.TimeoutError:
        await ctx.send("No response. Ending the game. Thanks for playing!")
        reset_game()

def reset_game():
    global game_started, joined_users, imposter, description_phase_started, user_descriptions
    game_started = False
    joined_users.clear()
    imposter = None
    description_phase_started = False
    user_descriptions.clear()

@client.command()
async def rules(ctx):
    rules_text = (
        "Word Imposter is a sneaky word-guessing game where players try to spot the imposter. "
        "One player doesn't know the chosen word, and everyone else takes turns describing it "
        "while the imposter tries to fit in. After three rounds, players vote on who they think "
        "doesn't know the word."
    )
    await ctx.send(rules_text)
@client.command()
async def help_adv(ctx):
    embed = Embed(title="Help", description="List of available commands:", color=0x00ff00)

    commands = {
        "play": "Start a new game or join an existing one by reacting with ✅.",
        "start": "Begin the game once all players have joined.",
        "describe": "Start the description phase where players describe their words.",
        "request <word>": "Add a new word to the nouns list.",
        "rules": "Show the rules of the game.",
        "force_quit": "Force quit the current game (admin only).",
        "status": "Show the current status of the game.",
        "players": "List all the players currently in the game.",
        "word <new_word>": "Set the word for the game manually (admin only).",
        "quit": "Leave the game before it starts.",
        "help": "Show this help message."
    }

    for command, description in commands.items():
        embed.add_field(name=f"!{command}", value=description, inline=False)

    await ctx.send(embed=embed)


@client.command()
async def status(ctx):
    global game_started, joined_users, description_phase_started
    status_message = f"Game Started: {game_started}\n"
    status_message += f"Description Phase Started: {description_phase_started}\n"
    status_message += f"Players Joined: {len(joined_users)}\n"
    for user_id in joined_users:
        user = await client.fetch_user(user_id)
        status_message += f"- {user.name}\n"
    await ctx.send(status_message)

@client.command()
async def players(ctx):
    global joined_users
    if not joined_users:
        await ctx.send("No players have joined yet.")
    else:
        players_message = "Current Players:\n"
        for user_id in joined_users:
            user = await client.fetch_user(user_id)
            players_message += f"- {user.name}\n"
        await ctx.send(players_message)

@client.command()
async def word(ctx, *, new_word: str):
    if ctx.author.guild_permissions.administrator:
        global game_word
        game_word = new_word
        await ctx.send(f"The word for the game has been set to: {new_word}")
    else:
        await ctx.send("You don't have permission to set the word.")

@client.command()
async def quit(ctx):
    global joined_users
    if ctx.author.id in joined_users:
        joined_users.remove(ctx.author.id)
        await ctx.send(f"{ctx.author.name} has left the game.")
    else:
        await ctx.send("You are not in the game.")




@client.command()
async def force_quit(ctx):
    global game_started
    if ctx.author.guild_permissions.administrator:
        if game_started:
            reset_game()
            await ctx.send("The game has been force quit.")
        else:
            await ctx.send("No game is currently in progress.")
    else:
        await ctx.send("You don't have permission to force quit the game.")

def generate_random_word(file_path):
    with open(file_path, 'r') as file:
        nouns = file.read().splitlines()
        return random.choice(nouns)

@client.command()
async def request(ctx, word):
    try:
        with open('nouns.txt', 'a') as file:
            file.write(word.strip() + '\n')
        await ctx.send(f"The word '{word}' has been added to the noun list.")
    except Exception as e:
        await ctx.send(f"An error occurred while adding the word: {e}")


def main():
    client.run(TOKEN)

if __name__ == '__main__':
    main()
