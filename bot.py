# bot.py
import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

from event import make_event_from_db
from database import create_connection
from raidbuilder import make_character_from_db
from emoji_dict import emoji_dict


def job_emoji_str(job_list):
    emoji_str = ""
    for job in job_list:
        emoji_str += emoji_dict[job] + " "
    return emoji_str


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

bot = commands.Bot(command_prefix='$')


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.command(name='hello', help='Answers with an appropriate hello message')
async def hello(ctx):
    options = [
        f'Ahoy {ctx.message.author.mention}!',
        f'Hello there, General {ctx.message.author.mention}!',
        f"What's up, {ctx.message.author.mention}?",
        f'Good day to you, {ctx.message.author.mention}!',
        f'Hooooi {ctx.message.author.mention}!',
        f'{ctx.message.author.mention}, thou hast summoned me?',
        f'Lali-ho, {ctx.message.author.mention}!',
    ]
    response = random.choice(options)
    await ctx.send(response)


@bot.command(name='talkin-shit', help='Posts THE best Namazu gif')
async def talkin_shit(ctx):
    await ctx.send('https://tenor.com/view/ffxiv-ff14-namazu-heard-you-talkin-shit-gif-15779424')


@bot.command(name='dm', help='Sends you a dm')
async def dm(ctx):
    await ctx.author.send('Hello')


@bot.command(name='display-event', help='displays an event from the database given its id')
async def display_event(ctx, event_id):
    conn = create_connection(r"database/test.db")
    if conn is not None:
        try:
            event = make_event_from_db(conn, event_id)
            embed = discord.Embed(title=f"**Event {event_id}**", color=discord.Color.dark_gold())
            embed.add_field(name="**Name**", value=event.name, inline=False)
            embed.add_field(name="**Participants**", value=event.participants_as_str(), inline=False)
            embed.add_field(name="**Jobs**", value=job_emoji_str(event.jobs), inline=False)
            embed.add_field(name="**Time**", value=event.get_time(), inline=False)
            embed.set_footer(text=f"This event is {event.state}")
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send(f'Could not find event with id {event_id}. This event might not exist (yet).')
    else:
        await ctx.send('Could not connect to database :(')


@bot.command(name='show-player', help='Displays characters registered with the given Discord ID')
async def show_player(ctx, discord_id):
    num_id = int(discord_id[3:-1])
    conn = create_connection(r"database/test.db")
    if conn is not None:
        try:  # TODO: handle multiple characters registered with the same discord id
            chara = make_character_from_db(conn, num_id, None)
            embed = discord.Embed(title=chara.character_name, description=job_emoji_str(chara.jobs),
                                  color=discord.Color.dark_gold())
            await ctx.send(f"<@{num_id}>'s character:", embed=embed)
        except Exception:
            await ctx.send(f'Could not find player with id {num_id}. This player might not be registered (yet).')
    else:
        await ctx.send('Could not connect to database :(')


# copied for reference
# @bot.command()
# async def embed(ctx):
#     embed=discord.Embed(
#     title="Text Formatting",
#         url="https://realdrewdata.medium.com/",
#         description="Here are some ways to format text",
#         color=discord.Color.blue())
#     embed.set_author(name="RealDrewData", url="https://twitter.com/RealDrewData", icon_url="https://cdn-images-1.medium.com/fit/c/32/32/1*QVYjh50XJuOLQBeH_RZoGw.jpeg")
#     #embed.set_author(name=ctx.author.display_name, url="https://twitter.com/RealDrewData", icon_url=ctx.author.avatar_url)
#     embed.set_thumbnail(url="https://i.imgur.com/axLm3p6.jpeg")
#     embed.add_field(name="*Italics*", value="Surround your text in asterisks (\*)", inline=False)
#     embed.add_field(name="**Bold**", value="Surround your text in double asterisks (\*\*)", inline=False)
#     embed.add_field(name="__Underline__", value="Surround your text in double underscores (\_\_)", inline=False)
#     embed.add_field(name="~~Strikethrough~~", value="Surround your text in double tildes (\~\~)", inline=False)
#     embed.add_field(name="`Code Chunks`", value="Surround your text in backticks (\`)", inline=False)
#     embed.add_field(name="Blockquotes", value="> Start your text with a greater than symbol (\>)", inline=False)
#     embed.add_field(name="Secrets", value="||Surround your text with double pipes (\|\|)||", inline=False)
#     embed.set_footer(text="Learn more here: realdrewdata.medium.com")
#     await ctx.send(embed=embed)


# @bot.event
# async def on_message(message: discord.Message):
#     if message.guild is None and not message.author.bot:
#         print(message.content)
#         await message.author.send(message.content)
#     else:
#         await bot.process_commands(message)

bot.run(TOKEN)
