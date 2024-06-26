from discord import Intents, Embed
from discord.ext import commands
import random
import asyncio
import os
import math
from t import TOKEN
import discord  
from discord.utils import get
from discord.ext.commands import MissingPermissions
intents = Intents.default()
intents.message_content = True
client = commands.Bot(command_prefix='?', intents=intents)

# Dictionary to store game states for each channel
games = {}

class GameState:
    def __init__(self):
        self.joined_users = []
        self.game_started = False
        self.imposter = None
        self.bot_emojis = {}
        self.voting_message = None
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
        await ctx.send("Message me the number 41")

@client.event
async def on_raw_reaction_add(payload):
    if payload.channel_id not in games:
        return

    game = games[payload.channel_id]

    if not game.game_started:
        if payload.emoji.name == "✅" and payload.message_id == game.message_id:
            if payload.member and not payload.member.bot:
                if payload.user_id not in game.joined_users:
                    game.joined_users.append(payload.user_id)
                    user = await client.fetch_user(payload.user_id)
                    await user.send("You have joined the queue")
    else:
        member = payload.member
        if member:
            print("Someone is using the bot")
        member = payload.member

def get_unused_word(words_file, used_words_file):
    with open(words_file, 'r') as f:
        words = f.read().splitlines()

    if os.path.exists(used_words_file):
        with open(used_words_file, 'r') as f:
            used_words = f.read().splitlines()
    else:
        used_words = []

    unused_words = list(set(words) - set(used_words))

    if not unused_words:
        # If all words have been used, reset the used words file
        with open(used_words_file, 'w') as f:
            f.write("")
        unused_words = words

    random_word = random.choice(unused_words)
    with open(used_words_file, 'a') as f:
        f.write(random_word + '\n')

    return random_word

@client.command()
async def start(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]

    if not game.game_started:
        if len(game.joined_users) > 2:
            random_word = get_unused_word('nouns.txt', 'used_words.txt')
            game.imposter = random.choice(game.joined_users)
            for user_id in game.joined_users:
                user = await client.fetch_user(user_id)
                if user_id == game.imposter:
                    await user.send("You are the imposter!")
                else:
                    await user.send(f"The word is: {random_word}")
            game.game_started = True
            await ctx.send("The game has started!")
        else:
            await ctx.send("Not enough users have joined yet.")
    else:
        await ctx.send("The game has already started.")

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
            await ctx.send(f"Round {round_number + 1}")
            joined_users = game.joined_users.copy()
            random.shuffle(joined_users)
            for user_id in joined_users:
                user = await client.fetch_user(user_id)
                await ctx.send(f"{user.mention}, please describe your word.")
                def check(m):
                    return m.author.id == user_id and m.channel == ctx.channel
                try:
                    description_msg = await client.wait_for('message', check=check, timeout=30)
                    if user_id not in game.user_descriptions:
                        game.user_descriptions[user_id] = []
                    game.user_descriptions[user_id].append(description_msg.content)
                except asyncio.TimeoutError:
                    await ctx.send(f"{user.mention}, you took too long to respond. Your description was not recorded.")
        await ctx.send("Description phase completed. Commence voting.")
        await start_voting(ctx)
    elif not game.game_started:
        await ctx.send("The game has not started yet.")
    else:
        await ctx.send("Description phase is already in progress.")

@client.command()
async def recall(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]
    if not game.user_descriptions:
        await ctx.send("No descriptions have been recorded yet.")
        return

    embed = discord.Embed(title="User Descriptions", color=discord.Color.blue())
    for user_id, descriptions in game.user_descriptions.items():
        user = await client.fetch_user(user_id)
        description_list = "\n".join([f"{i+1}. {desc}" for i, desc in enumerate(descriptions)])
        embed.add_field(name=user.name, value=description_list, inline=False)

    await ctx.send(embed=embed)

@client.command()
async def start_voting(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]
    try:
        embed = discord.Embed(title="Vote for the Imposter", description="React with the number corresponding to the user you suspect is the imposter.", color=0xff0000)

        for index, user_id in enumerate(game.joined_users, start=1):
            user = await client.fetch_user(user_id)
            embed.add_field(name=f"{index}. {user.name}", value=user.id, inline=False)

        voting_message = await ctx.send(embed=embed)

        number_emojis = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣']
        bot_emojis = {number_emojis[i]: game.joined_users[i] for i in range(len(game.joined_users))}

        for emoji in bot_emojis:
            await voting_message.add_reaction(emoji)
            await asyncio.sleep(1)

        game.voting_message = voting_message
        game.bot_emojis = bot_emojis
        game.votes = {user_id: 0 for user_id in game.joined_users}
        game.voted_users = set()

        await ctx.send("Voting has started. Use the reactions to vote.")
    except Exception as e:
        await ctx.send(f"An error occurred during the voting process: {e}")
        print(f"Error during voting process: {e}")
        import traceback
        traceback.print_exc()

@client.event
async def on_reaction_add(reaction, user):
    channel_id = reaction.message.channel.id
    if channel_id not in games:
        return

    game = games[channel_id]
    if reaction.message.id != game.voting_message.id:
        return

    if user.id not in game.joined_users:
        return

    if user.id in game.voted_users:
        await user.send("You have already voted. You cannot vote twice.")
        await reaction.message.remove_reaction(reaction.emoji, user)
        return

    voted_user_id = game.bot_emojis.get(str(reaction.emoji))
    if voted_user_id == user.id:
        await user.send("You cannot vote for yourself. Please vote again.")
        await reaction.message.remove_reaction(reaction.emoji, user)
        return

    game.voted_users.add(user.id)
    game.votes[voted_user_id] += 1

    await user.send("Your vote has been counted.")

@client.command()
async def tally(ctx):
    if ctx.channel.id not in games:
        await ctx.send("No game has been set up in this channel. Use ?play to start a new game.")
        return

    game = games[ctx.channel.id]
    if not game.votes:
        await ctx.send("No votes have been cast yet.")
        return

    # Tally votes and determine the result
    await asyncio.sleep(2)
    majority_vote = max(game.votes.values(), default=0)
    voted_user_ids = [user_id for user_id, count in game.votes.items() if count == majority_vote]

    if len(voted_user_ids) == 1:
        voted_user_id = voted_user_ids[0]
        if voted_user_id == game.imposter:
            await ctx.send(f"Congratulations! You win. The user you suspected ({(await client.fetch_user(voted_user_id)).name}) was the imposter!")
        else:
            imposter_user = await client.fetch_user(game.imposter)
            await ctx.send(f"Sorry, you lose. The imposter was {imposter_user.name}.")
    else:
        imposter_user = await client.fetch_user(game.imposter)
        await ctx.send(f"There was a tie in the votes. No majority decision was made. The imposter was {imposter_user.name}.")

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
        "start_voting": "Start the voting phase after the description phase.",
        "tally": "Tally the votes and determine the imposter.",
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
        "word <new_word>": "Set the word for the game manually (admin only).",
        "help_adv": "Show this help message.",
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
            pass
            
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
