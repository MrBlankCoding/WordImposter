from discord import Intents, Embed
from discord.ext import commands
from discord.ext.commands import MemberConverter
import random
import asyncio
import math
import logging
from discord.utils import get
from discord.ext.commands import MissingPermissions
import discord  
from discord.utils import get
from discord.ext.commands import MissingPermissions
intents = Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='?', intents=intents)
TOKEN = ""


games = {}

class GameState:
    def __init__(self):
        self.joined_users = []
        self.game_started = False
        self.imposter = None
        self.description_phase_started = False
        self.user_descriptions = {}
        self.num_rounds = 3

@client.event
async def on_ready():
    print('Bot is ready.')

@client.command()
async def play(ctx):
    if ctx.channel.id not in games:
        games[ctx.channel.id] = GameState()

    game = games[ctx.channel.id]

    if not game.game_started:
        embed = Embed(title="Game Start", description="React with ✅ if you want to play!", color=0x00ff00)
        message = await ctx.send(embed=embed)
        game.message_id = message.id
        await message.add_reaction("✅")
    else:
        await ctx.send("A game has already started. You cannot join now.")

@client.command()
async def hard(ctx):
    if ctx.channel.id not in games:
        games[ctx.channel.id] = GameState()

    game = games[ctx.channel.id]

    if not game.game_started:
        embed = Embed(title="Hard Mode Game Start", description="React with 🟥 if you want to play!", color=0xff0000)
        message = await ctx.send(embed=embed)
        game.message_id = message.id
        await message.add_reaction("🟥")
    else:
        await ctx.send("A game has already started. You cannot join now.")

@client.event
async def on_raw_reaction_add(payload):
    if payload.channel_id not in games:
        return

    game = games[payload.channel_id]

    if not game.game_started:
        if payload.emoji.name in ["✅", "🟥"] and payload.message_id == game.message_id:
            if payload.member and not payload.member.bot:
                if payload.user_id not in game.joined_users:
                    game.joined_users.append(payload.user_id)
                    user = await client.fetch_user(payload.user_id)
                    await user.send("You have joined the queue")
    else:
        member = payload.member
        if member:
            print("Someone is using the bot")

@client.command()
async def start(ctx, mode='normal'):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play or ?hard to set up a game.")
        return

    game = games[ctx.channel.id]

    if not game.game_started:
        if len(game.joined_users) > 2:
            random_word = generate_random_word('nouns.txt')
            
            if mode == 'hard' and len(game.joined_users) > 7:
                imposters = random.sample(game.joined_users, 2)
            else:
                imposters = [random.choice(game.joined_users)]
                
            for user_id in game.joined_users:
                user = await client.fetch_user(user_id)
                if user_id in imposters:
                    await user.send("You are an imposter!")
                else:
                    await user.send(f"Your random word: {random_word}")
                    
            game.game_started = True
            await ctx.send("The game has started!")
        else:
            await ctx.send("Not enough users have joined yet.")
    else:
        await ctx.send("A game has already started.")
        
@client.command()
async def describe(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]

    if game.game_started and not game.description_phase_started:
        game.description_phase_started = True
        await ctx.send("Description phase has started. Users, please describe your words one by one.")
        for round_number in range(game.num_rounds):
            await ctx.send(f"**Round {round_number + 1}**")
            for user_id in game.joined_users:
                user = await client.fetch_user(user_id)
                await ctx.send(f"{user.mention}, please describe your word.")
                def check(m):
                    return m.author.id == user_id and m.channel == ctx.channel
                try:
                    description_msg = await client.wait_for('message', check=check, timeout=30)
                    game.user_descriptions[user_id] = description_msg.content
                except asyncio.TimeoutError:
                    await ctx.send(f"{user.mention}, you took too long to respond. Your description was not recorded.")
        await ctx.send("Description phase completed. Commence voting.")
        await start_voting(ctx)
    elif not game.game_started:
        await ctx.send("The game has not started yet.")
    else:
        await ctx.send("Description phase is already in progress.")



logging.basicConfig(level=logging.INFO)

async def start_voting(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play or ?hard to start a new game.")
        return

    game = games[ctx.channel.id]

    embed = Embed(title="Vote for the Imposter", description="React with the number corresponding to the user you suspect is the imposter.", color=0xff0000)
    
    try:
        for index, user_id in enumerate(game.joined_users, start=1):
            user = await client.fetch_user(user_id)
            embed.add_field(name=f"{index}. {user.name}", value=user.id, inline=False)
        
        voting_message = await ctx.send(embed=embed)
        
        for i in range(1, len(game.joined_users) + 1):
            await voting_message.add_reaction(str(i) + '️⃣')
            await asyncio.sleep(1)

        voted_users = set()
        votes = [0] * len(game.joined_users)

        def check(reaction, user):
            return user.id in game.joined_users and str(reaction.emoji)[0].isdigit() and user.id not in voted_users

        try:
            while len(voted_users) < len(game.joined_users):
                reaction, user = await client.wait_for('reaction_add', check=check, timeout=30)
                voted_users.add(user.id)
                voted_user_index = int(str(reaction.emoji)[0]) - 1
                votes[voted_user_index] += 1

            await ctx.send("Voting time has expired. Tallying votes...")

            max_votes = max(votes)
            max_voted_users = [i for i, v in enumerate(votes) if v == max_votes]

            for reaction in voting_message.reactions:
                await reaction.clear()

            if len(max_voted_users) == 1:
                voted_user_index = max_voted_users[0]
                voted_user_id = game.joined_users[voted_user_index]
                voted_user = await client.fetch_user(voted_user_id)

                if isinstance(game.imposter, list):
                    if voted_user_id in game.imposter:
                        await ctx.send(f"Congratulations! The majority voted for one of the imposters: {voted_user.name}. You win!")
                    else:
                        imposter_users = [await client.fetch_user(imposter_id) for imposter_id in game.imposter]
                        imposters_names = ', '.join(user.name for user in imposter_users)
                        await ctx.send(f"Sorry, you lose. The majority voted for {voted_user.name}, but the imposters were {imposters_names}.")
                else:
                    if voted_user_id == game.imposter:
                        await ctx.send(f"Congratulations! The majority voted for the imposter: {voted_user.name}. You win!")
                    else:
                        imposter_user = await client.fetch_user(game.imposter)
                        await ctx.send(f"Sorry, you lose. The majority voted for {voted_user.name}, but the imposter was {imposter_user.name}.")
            else:
                await ctx.send("There was a tie in the votes. No majority decision was made.")

            await ask_replay(ctx)
        except asyncio.TimeoutError:
            await ctx.send("Voting time has expired.")

            for reaction in voting_message.reactions:
                await reaction.clear()

            max_votes = max(votes)
            max_voted_users = [i for i, v in enumerate(votes) if v == max_votes]

            if len(max_voted_users) == 1:
                voted_user_index = max_voted_users[0]
                voted_user_id = game.joined_users[voted_user_index]
                voted_user = await client.fetch_user(voted_user_id)

                if isinstance(game.imposter, list):
                    if voted_user_id in game.imposter:
                        await ctx.send(f"Congratulations! The majority voted for one of the imposters: {voted_user.name}. You win!")
                    else:
                        imposter_users = [await client.fetch_user(imposter_id) for imposter_id in game.imposter]
                        imposters_names = ', '.join(user.name for user in imposter_users)
                        await ctx.send(f"Sorry, you lose. The majority voted for {voted_user.name}, but the imposters were {imposters_names}.")
                else:
                    if voted_user_id == game.imposter:
                        await ctx.send(f"Congratulations! The majority voted for the imposter: {voted_user.name}. You win!")
                    else:
                        imposter_user = await client.fetch_user(game.imposter)
                        await ctx.send(f"Sorry, you lose. The majority voted for {voted_user.name}, but the imposter was {imposter_user.name}.")
            else:
                imposter_users = [await client.fetch_user(imposter_id) for imposter_id in game.imposter]
                imposters_names = ', '.join(user.name for user in imposter_users)
                await ctx.send(f"There was a tie in the votes. No majority decision was made. The imposters were {imposters_names}.")

            await ask_replay(ctx)
    except Exception as e:
        logging.error(f"An error occurred during the voting process: {e}")
        await ctx.send("An error occurred during the voting process. Please try again.")
        for reaction in voting_message.reactions:
            await reaction.clear()
        await ask_replay(ctx)

async def ask_replay(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]
    embed = Embed(title="Play Again?", description="React with ✅ to play again or ❌ to end the game.", color=0x00ff00)
    message = await ctx.send(embed=embed)
    await message.add_reaction("✅")
    await message.add_reaction("❌")

    def check(reaction, user):
        return user.id in game.joined_users and str(reaction.emoji) in ["✅", "❌"]

    try:
        reaction, user = await client.wait_for('reaction_add', check=check, timeout=60)
        if str(reaction.emoji) == "✅":
            await ctx.send("Starting a new game!")
            reset_game(ctx.channel.id)
            await play(ctx)
        else:
            await ctx.send("Ending the game. Thanks for playing!")
            reset_game(ctx.channel.id)
    except asyncio.TimeoutError:
        await ctx.send("No response. Ending the game. Thanks for playing!")
        reset_game(ctx.channel.id)

def reset_game(channel_id):
    if channel_id in games:
        del games[channel_id]

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
        "rounds <number>": "Set the number of description rounds.",
        "rules": "Show the rules of the game.",
        "status": "Show the current status of the game.",
        "players": "List all the players currently in the game.",
        "quit": "Leave the game before it starts.",
        "kick <user>": "Kick a player from the game (admin only).",
        "wordlist": "View the list of words available for the game.",
        "removeword <line_number>": "Remove a word from the word list by its line number (admin only).",
        "request <word>": "Add a new word to the nouns list.",
        "resets": "Reset the current game (admin only).",
        "hard": "sets it to 2 imposters if there is more than 7 players",
        "word <new_word>": "Set the word for the game manually (admin only).",
    }

    for command, description in commands.items():
        embed.add_field(name=f"?{command}", value=description, inline=False)

    await ctx.send(embed=embed)
@client.command()
async def status(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]

    status_message = f"Game Started: {game.game_started}\n"
    status_message += f"Description Phase Started: {game.description_phase_started}\n"
    status_message += f"Players Joined: {len(game.joined_users)}\n"
    for user_id in game.joined_users:
        user = await client.fetch_user(user_id)
        status_message += f"- {user.name}\n"
    await ctx.send(status_message)

@client.command()
async def players(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]

    if not game.joined_users:
        await ctx.send("No players have joined yet.")
    else:
        players_message = "Current Players:\n"
        for user_id in game.joined_users:
            user = await client.fetch_user(user_id)
            players_message += f"- {user.name}\n"
        await ctx.send(players_message)

@client.command()
async def word(ctx, *, new_word: str):
    if ctx.author.guild_permissions.administrator:
        if ctx.channel.id not in games:
            await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
            return

        game = games[ctx.channel.id]
        game.word = new_word
        await ctx.send(f"The word for the game has been set to: {new_word}")
    else:
        await ctx.send("You don't have permission to set the word.")

@client.command()
async def quit(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]

    if ctx.author.id in game.joined_users:
        game.joined_users.remove(ctx.author.id)
        await ctx.send(f"{ctx.author.name} has left the game.")
    else:
        await ctx.send("You are not in the game.")

@client.command()
async def mute(ctx, member: discord.Member, duration: int):
    if ctx.author.name != "mrblank7604":
        await ctx.send("You do not have permission to use this command.")
        return

    # Create a muted role if it doesn't exist
    muted_role = get(ctx.guild.roles, name="Muted")
    if not muted_role:
        try:
            muted_role = await ctx.guild.create_role(name="Muted", permissions=discord.Permissions(send_messages=False))
            for channel in ctx.guild.channels:
                await channel.set_permissions(muted_role, send_messages=False, speak=False)
        except MissingPermissions:
            await ctx.send("I do not have permission to create a 'Muted' role.")
            return

    # Add the muted role to the user
    await member.add_roles(muted_role)
    await ctx.send(f"User {member.display_name} has been muted for {duration} minutes.")

    # Wait for the specified duration then remove the role
    await asyncio.sleep(duration * 60)
    await member.remove_roles(muted_role)
    await ctx.send(f"User {member.display_name} has been unmuted.")

        
@client.command()
@commands.has_permissions(administrator=True)
async def kick(ctx, member: commands.MemberConverter):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel.")
        return

    game = games[ctx.channel.id]

    if member.id in game.joined_users:
        game.joined_users.remove(member.id)
        await ctx.send(f"{member.name} has been kicked from the game.")
        try:
            await member.send("You have been kicked from the game by an administrator.")
        except:
            pass  # If the user has DMs disabled, we can't notify them
    else:
        await ctx.send(f"{member.name} is not in the game.")

@kick.error
async def kick_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please mention a valid member of this server.")
    else:
        await ctx.send("An error occurred while trying to kick the member.")


@client.command()
async def rounds(ctx, num_rounds: int):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]

    if num_rounds < 1:
        await ctx.send("The number of rounds must be at least 1.")
    else:
        game.num_rounds = num_rounds
        await ctx.send(f"The number of description rounds has been set to {num_rounds}.")

@client.command()
async def resets(ctx):
    if ctx.author.guild_permissions.administrator:
        if ctx.channel.id not in games:
            await ctx.send("No game has been set up in this channel.")
            return

        game = games[ctx.channel.id]

        if game.game_started:
            reset_game(ctx.channel.id)
            await ctx.send("The game has been force quit.")
        else:
            await ctx.send("No game is currently in progress.")
    else:
        await ctx.send("You don't have permission to force quit the game.")
        

@client.command()
@commands.has_permissions(administrator=True)
async def removeword(ctx, line_number: int):
    try:
        with open('nouns.txt', 'r') as file:
            words = file.read().splitlines()

        if 0 < line_number <= len(words):
            removed_word = words.pop(line_number - 1)
            with open('nouns.txt', 'w') as file:
                file.write("\n".join(words) + "\n")
            await ctx.send(f"The word '{removed_word}' has been removed from the word list.")
        else:
            await ctx.send(f"Invalid line number. Please provide a number between 1 and {len(words)}.")
    except FileNotFoundError:
        await ctx.send("The word list file was not found.")
    except Exception as e:
        await ctx.send(f"An error occurred while removing the word: {e}")

@client.command()
async def wordlist(ctx):
    try:
        with open('nouns.txt', 'r') as file:
            words = file.read().splitlines()
            if not words:
                await ctx.send("The word list is currently empty.")
                return
            
            pages = math.ceil(len(words) / 20)
            current_page = 0

            def get_page_embed(page):
                embed = Embed(title=f"Word List (Page {page + 1}/{pages})", color=0x00ff00)
                start = page * 20
                end = start + 20
                for i, word in enumerate(words[start:end], start=start + 1):
                    embed.add_field(name=f"{i}.", value=word, inline=False)
                return embed
            
            message = await ctx.send(embed=get_page_embed(current_page))

            if pages > 1:
                await message.add_reaction('⬅️')
                await message.add_reaction('➡️')

                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in ['⬅️', '➡️'] and reaction.message.id == message.id

                while True:
                    try:
                        reaction, user = await client.wait_for('reaction_add', check=check, timeout=60.0)
                        
                        if str(reaction.emoji) == '➡️':
                            if current_page < pages - 1:
                                current_page += 1
                                await message.edit(embed=get_page_embed(current_page))
                            await message.remove_reaction(reaction, user)

                        elif str(reaction.emoji) == '⬅️':
                            if current_page > 0:
                                current_page -= 1
                                await message.edit(embed=get_page_embed(current_page))
                            await message.remove_reaction(reaction, user)
                    
                    except asyncio.TimeoutError:
                        break

                await message.clear_reactions()

    except FileNotFoundError:
        await ctx.send("The word list file was not found.")
    except Exception as e:
        await ctx.send(f"An error occurred while retrieving the word list: {e}")
def generate_random_word(file_path):
    try:
        with open(file_path, 'r') as file:
            nouns = file.read().splitlines()
            return random.choice(nouns)
    except FileNotFoundError:
        return "default_word"  # Default word if the file is not found
        
@removeword.error
async def removeword_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("You do not have permission to use this command.")
    elif isinstance(error, commands.BadArgument):
        await ctx.send("Please provide a valid word to remove.")
    else:
        await ctx.send("An error occurred while trying to remove the word.")

@client.command()
async def request(ctx, word):
    word = word.strip()  # Strip any extra whitespace
    try:
        # Read the existing words from the file
        with open('nouns.txt', 'r') as file:
            existing_words = file.read().splitlines()

        # Check if the word is already in the list
        if word in existing_words:
            await ctx.send(f"The word '{word}' is already in the noun list.")
        else:
            # If not, add the word to the file
            with open('nouns.txt', 'a') as file:
                file.write(word + '\n')
            await ctx.send(f"The word '{word}' has been added to the noun list.")
    except FileNotFoundError:
        # If the file does not exist, create it and add the word
        with open('nouns.txt', 'w') as file:
            file.write(word + '\n')
        await ctx.send(f"The word '{word}' has been added to the noun list.")
    except Exception as e:
        await ctx.send(f"An error occurred while adding the word: {e}")

def main():
    client.run(TOKEN)

if __name__ == '__main__':
    main()
