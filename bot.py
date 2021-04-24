# bot.py
import datetime
import os
import random
import traceback

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pytz import timezone
from pytz.exceptions import UnknownTimeZoneError

from event import make_event_from_db, Event
from database import create_connection, create_event
from raidbuilder import make_character_from_db
from emoji_dict import emoji_dict


def job_emoji_str(job_list):
    emoji_str = ""
    for job in job_list:
        emoji_str += emoji_dict[job] + " "
    return emoji_str


def role_num_emoji_str(n_tanks, n_healers, n_dps):
    return f"{n_tanks} {emoji_dict['Tank']} {n_healers} {emoji_dict['Healer']} {n_dps} {emoji_dict['DPS']}"


load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents().default()
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)


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
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        try:
            event = make_event_from_db(conn, event_id)
            try:
                creator = ctx.guild.get_member(event.creator_id)
                creator_name = creator.name if creator.nick is None else creator.nick
            except Exception:
                creator_name = "INVALID_MEMBER"
            embed = discord.Embed(title=f"**Event {event_id}**",
                                  description=f"Organized by **{creator_name}**",
                                  color=discord.Color.dark_gold())
            embed.add_field(name="**Name**", value=event.name, inline=False)
            if event.participant_names:
                embed.add_field(name="**Participants**", value=event.participants_as_str(), inline=False)
            if event.jobs:
                embed.add_field(name="**Jobs**", value=job_emoji_str(event.jobs), inline=False)
            else:
                embed.add_field(name="**Required Roles**", value=role_num_emoji_str(*event.role_numbers), inline=False)
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


@bot.command(name='make-event', help='creates an event given parameters: '
                                     'name, date (format d-m-y), time (format HH:MM), '
                                     'num_Tanks, num_Heals, num_DPS, timezone (optional, default GMT)')
async def make_event(ctx, name, date, start_time, num_tanks, num_heals, num_dps, user_timezone="GMT"):
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        try:
            tz = timezone(user_timezone)
        except Exception:
            await ctx.send(f"Unknown timezone {user_timezone}, use format like 'Europe/Amsterdam'")
            return

        try:
            d, m, y = date.split("-")
            hour, minute = start_time.split(":")
            dt_obj = datetime.datetime(int(y), int(m), int(d), int(hour), int(minute), tzinfo=tz)
        except Exception:
            await ctx.send(f"Could not parse date and/or time, make sure to format like this: "
                           f"dd-mm-yyyy hh:mm (in 24 hour format)")
            return

        event_tup = (name, int(dt_obj.timestamp()), None, None, None,
                     None, f"{num_tanks},{num_heals},{num_dps}", int(ctx.message.author.mention[2:-1]), "RECRUITING")
        ev_id = create_event(conn, event_tup)

        try:
            event = make_event_from_db(conn, ev_id)
            try:
                creator = ctx.guild.get_member(event.creator_id)
                creator_name = creator.name if creator.nick is None else creator.nick
            except Exception:
                creator_name = "INVALID_MEMBER"
            embed = discord.Embed(title=f"**Event {ev_id}**",
                                  description=f"Organized by **{creator_name}**",
                                  color=discord.Color.dark_gold())
            embed.add_field(name="**Name**", value=event.name, inline=False)
            if event.participant_names:
                embed.add_field(name="**Participants**", value=event.participants_as_str(), inline=False)
            if event.jobs:
                embed.add_field(name="**Jobs**", value=job_emoji_str(event.jobs), inline=False)
            else:
                embed.add_field(name="**Required Roles**", value=role_num_emoji_str(*event.role_numbers), inline=False)
            embed.add_field(name="**Time**", value=event.get_time(), inline=False)
            embed.set_footer(text=f"This event is {event.state}")
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send(f'Could not find event with id {ev_id}. This event might not exist (yet).')
    else:
        await ctx.send('Could not connect to database. Need connection to create and save events.')


@bot.event
async def on_command_error(ctx, error):
    # adapted from RemixBot https://github.com/cree-py/RemixBot
    send_help = (commands.MissingRequiredArgument, commands.BadArgument, commands.TooManyArguments, commands.UserInputError)

    if isinstance(error, commands.CommandNotFound):  # fails silently
        pass

    elif isinstance(error, send_help):
        _help = await send_cmd_help(ctx)
        await ctx.send(embed=_help)

    elif isinstance(error, commands.CommandOnCooldown):
        await ctx.send(f'This command is on cooldown. Please wait {error.retry_after:.2f}s')

    elif isinstance(error, commands.MissingPermissions):
        await ctx.send('You do not have the permissions to use this command.')
    # If any other error occurs, prints to console.
    else:
        print(''.join(traceback.format_exception(type(error), error, error.__traceback__)))


async def send_cmd_help(ctx):
    cmd = ctx.command
    em = discord.Embed(title=f'Usage: {ctx.prefix + cmd.signature}', color=discord.Color.dark_gold())
    em.description = cmd.help
    return em


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
