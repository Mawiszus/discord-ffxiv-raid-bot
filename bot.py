# bot.py
import datetime
import os
import random
import traceback
import asyncio

import discord
from discord.ext import commands
from dotenv import load_dotenv
from pytz import timezone
from pytz.exceptions import UnknownTimeZoneError

from event import make_event_from_db, Event
from database import create_connection, create_event, update_event, find_events, col_str, get_player_by_id
from database import create_player, delete_player, update_player
from raidbuilder import make_character_from_db, Character
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


def make_event_embed(ev: Event, guild, add_legend=False):
    try:
        creator = guild.get_member(ev.creator_id)
        creator_name = creator.name if creator.nick is None else creator.nick
    except Exception:
        creator_name = "INVALID_MEMBER"
    embed = discord.Embed(title=f"**Event {ev.id}**",
                          description=f"Organized by **{creator_name}**",
                          color=discord.Color.dark_gold())
    embed.add_field(name="**Name**", value=ev.name, inline=False)
    embed.add_field(name="**Time**", value=ev.get_time(), inline=False)

    signed_str, bench_str = ev.signed_in_and_benched_as_strs()
    if signed_str:
        embed.add_field(name="**Participants**", value=signed_str, inline=False)
    if bench_str:
        embed.add_field(name="**On the bench**", value=bench_str, inline=False)
    if ev.jobs:
        embed.add_field(name="**Jobs**", value=job_emoji_str(ev.jobs), inline=False)
    else:
        embed.add_field(name="**Required Roles**", value=role_num_emoji_str(*ev.role_numbers), inline=False)

    if add_legend:
        embed.add_field(name="Use reactions to", value=f"{emoji_dict['sign_in']} - sign up"
                                                       f"\n{emoji_dict['bench']} - substitute bench"
                                                       f"\n{emoji_dict['sign_out']} - sign out", inline=False)

    embed.set_footer(text=f"This event is {ev.state}")
    return embed


def make_character_embed(ch: Character, date, num_raids):
    embed = discord.Embed(title=ch.character_name, description=job_emoji_str(ch.jobs),
                          color=discord.Color.dark_gold())
    embed.add_field(name="**Nr. of Events:**", value=str(num_raids), inline=False)
    embed.add_field(name="**Involuntarily benched counter:**", value=str(ch.involuntary_benches),
                    inline=False)
    embed.set_footer(text=f"Registered since {date}")
    return embed


@bot.command(name='display-event', help='displays an event from the database given its id')
async def display_event(ctx, event_id):
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        try:
            event = make_event_from_db(conn, event_id)
            embed = make_event_embed(event, ctx.guild)
            if event.message_link:
                embed.add_field(name="**Link to original post**", value=event.message_link, inline=False)
            await ctx.send(embed=embed)
        except Exception:
            await ctx.send(f'Could not find event with id {event_id}. This event might not exist (yet).')
    else:
        await ctx.send('Could not connect to database :(')


@bot.command(name='show-player', help='Displays characters registered with the given Discord ID')
async def show_player(ctx, discord_id):
    num_id = int(discord_id[3:-1])
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        try:  # TODO: handle multiple characters registered with the same discord id
            chara, date, num_raids = make_character_from_db(conn, num_id, None)
            embed = make_character_embed(chara, date, num_raids)
            await ctx.send(f"<@{num_id}>'s character:", embed=embed)
        except Exception:
            await ctx.send(f'Could not find character with id <@{num_id}>. This player might not be registered (yet).')
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
                     None, f"{num_tanks},{num_heals},{num_dps}",
                     int(ctx.message.author.mention[2:-1]), None, "RECRUITING")
        ev_id = create_event(conn, event_tup)

        try:
            event = make_event_from_db(conn, ev_id)
        except Exception:
            await ctx.send(f'Could not find event with id {ev_id}. This event might not exist (yet).')
            return
        embed = make_event_embed(event, ctx.guild, True)
        message = await ctx.send(embed=embed)
        update_event(conn, "message_link", message.jump_url, ev_id)
        await message.add_reaction(emoji_dict["sign_in"])
        await message.add_reaction(emoji_dict["bench"])
        await message.add_reaction(emoji_dict["sign_out"])
        return
    else:
        await ctx.send('Could not connect to database. Need connection to create and save events.')
        return


@bot.command(name='register-character', help='Registers a character given parameters: name ("Firstname Lastname"), '
                                             'job_list (formatted like "JOB,JOB,JOB", given in order of your priority)')
async def register_character(ctx, name, job_list):
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, date, num_raids = make_character_from_db(conn, disc_id, None)
            embed = make_character_embed(chara, date, num_raids)
            await ctx.send(f"There is already a character registered by <@{disc_id}>, "
                           f"multiple characters are not supported (yet).", embed=embed)
            return
        try:
            chara = Character(disc_id, name, job_list, 0)
            player = (chara.discord_id, name, job_list, datetime.datetime.today().strftime('%Y-%m-%d'), 0, 0)
            create_player(conn, player)
            embed = make_character_embed(chara, player[3], player[4])
            await ctx.send(f"<@{chara.discord_id}>'s character:", embed=embed)
        except Exception:
            await ctx.send('Could not parse name and/or job list. '
                           'Format like this: "Firstname Lastname", "JOB,JOB,JOB"')
            return

    else:
        await ctx.send('Could not connect to database. Need connection to create and save characters.')
        return


@bot.command(name='delete-character', help='Deletes the character registered with your discord id.')
async def delete_character(ctx):
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, _, _ = make_character_from_db(conn, disc_id, None)
            delete_player(conn, disc_id, chara.character_name)
            await ctx.send(f'Character **{chara.character_name}** by <@{disc_id}> is now deleted.')
            return
        else:
            await ctx.send(f'There is no character registered by <@{disc_id}> to delete.')
            return
    else:
        await ctx.send('Could not connect to database. Need connection to delete characters.')
        return


@bot.command(name='add-job', help="adds given job at given position in your character's job list. "
                                  "Pos 0 is in front of 1st job, pos 1 in front of 2nd job etc.")
async def add_job(ctx, job, pos):
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, date, num_raids = make_character_from_db(conn, disc_id, None)
            job_list = chara.jobs
            try:
                job_list.insert(int(pos), job.upper())
            except Exception:
                await ctx.send(f'Could not parse position. '
                               f'Position needs to be a valid insertion number for your job list.')
                return
            try:
                chara.set_jobs(job_list)
            except SyntaxError as e:
                await ctx.send(f'Could not add job. {e.msg}.')
                return
            update_player(conn, "jobs", col_str(chara.jobs), disc_id, chara.character_name)
            embed = make_character_embed(chara, date, num_raids)
            await ctx.send(f"<@{chara.discord_id}>'s character:", embed=embed)
            return
        else:
            await ctx.send(f'There is no character registered by <@{disc_id}> to add jobs to.')
            return
    else:
        await ctx.send('Could not connect to database. Need connection to edit characters.')
        return


@bot.command(name='remove-job', help="removes the given job from your character's job list.")
async def remove_job(ctx, job):
    conn = create_connection(r"database/test_2.db")
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, date, num_raids = make_character_from_db(conn, disc_id, None)
            try:
                chara.jobs.remove(job.upper())
            except ValueError:
                await ctx.send(f'Job {job.upper()} is not in your job list.')
                return

            update_player(conn, "jobs", col_str(chara.jobs), disc_id, chara.character_name)
            embed = make_character_embed(chara, date, num_raids)
            await ctx.send(f"<@{chara.discord_id}>'s character:", embed=embed)
            return
        else:
            await ctx.send(f'There is no character registered by <@{disc_id}> to remove jobs from.')
            return
    else:
        await ctx.send('Could not connect to database. Need connection to edit characters.')
        return


@bot.event
async def on_raw_reaction_add(reaction):
    emoji = reaction.emoji
    user = reaction.member
    if user.bot:
        return
    if emoji.name in [emoji_dict['sign_in'].split(":")[1],
                      emoji_dict['bench'].split(":")[1],
                      emoji_dict['sign_out'].split(":")[1]]:
        message = await bot.get_guild(reaction.guild_id).get_channel(reaction.channel_id).fetch_message(reaction.message_id)
        # Find corresponding event
        conn = create_connection(r"database/test_2.db")
        if conn is not None:
            db_ev = find_events(conn, "message_link", message.jump_url)
            if not db_ev:
                # Reaction was not on an event post
                return
            event = Event(*db_ev[0])
            if event.state != "RECRUITING":
                await user.send(f'You are trying to sign in/out for Event {event.id}, '
                                f'but the recruitment has ended.')
                await message.remove_reaction(emoji, user)
                return

            if user.id in event.participant_ids:
                idx = event.participant_ids.index(user.id)
                if emoji.name == emoji_dict['sign_out'].split(":")[1]:
                    del event.participant_ids[idx]
                    del event.is_bench[idx]
                    del event.participant_names[idx]
                    update_event(conn,  "participant_names", col_str(event.participant_names), event.id)
                    update_event(conn,  "participant_ids", col_str(event.participant_ids), event.id)
                    update_event(conn,  "is_bench", col_str(event.is_bench), event.id)
                    embed = make_event_embed(event, message.guild, True)
                    await message.edit(embed=embed)
                    await user.send(f'You are now signed out of {event.id}!')
                    await message.remove_reaction(emoji, user)
                    return
                elif emoji.name == emoji_dict['bench'].split(":")[1]:
                    if event.is_bench[idx] == 0:
                        # person is not benched and wants to be benched
                        # if it is already 1, person is already benched, nothing happens
                        event.is_bench[idx] = 1
                        update_event(conn, "is_bench", col_str(event.is_bench), event.id)
                        embed = make_event_embed(event, message.guild, True)
                        await message.edit(embed=embed)
                        await message.remove_reaction(emoji, user)
                        return
                elif emoji.name == emoji_dict['sign_in'].split(":")[1]:
                    if event.is_bench[idx] == 1:
                        # person is benched and wants to be signed up normally
                        # if it is already 0, person is already signed up, nothing happens
                        event.is_bench[idx] = 0
                        update_event(conn, "is_bench", col_str(event.is_bench), event.id)
                        embed = make_event_embed(event, message.guild, True)
                        await message.edit(embed=embed)
                        await message.remove_reaction(emoji, user)
                        return
            else:
                # user not in list yet
                if not emoji.name == emoji_dict['sign_out'].split(":")[1]:  # if they aren't signed in, "sign_out" will not do anything
                    db_player = get_player_by_id(conn, user.id)
                    if not db_player:
                        # user also not in db
                        await user.send(f'You are trying to sign in to Event {event.id}, '
                                        f'but you are not registered yet! '
                                        f'Please register with $register-character on your server')
                        await message.remove_reaction(emoji, user)
                        return
                    chara, _, _ = make_character_from_db(conn, user.id, None)
                    if emoji.name == emoji_dict['sign_in'].split(":")[1]:
                        bench = 0
                    else:
                        bench = 1
                    event.participant_names.append(chara.character_name)
                    event.participant_ids.append(chara.discord_id)
                    event.is_bench.append(bench)
                    update_event(conn, "participant_names", col_str(event.participant_names), event.id)
                    update_event(conn, "participant_ids", col_str(event.participant_ids), event.id)
                    update_event(conn, "is_bench", col_str(event.is_bench), event.id)
                    embed = make_event_embed(event, message.guild, True)
                    await message.edit(embed=embed)
                    await user.send(f'You are now signed in for {event.id}!')
                    await message.remove_reaction(emoji, user)
                    return

            # await user.send(f'You are trying to sign in to Event {event.id}!')
            await message.remove_reaction(emoji, user)
            return
        else:
            await message.remove_reaction(emoji, user)
            await user.send('Could not connect to database to process you signing in. '
                            'Please contact an admin for this bot.')
            return
    else:
        return


# @bot.event
# async def on_raw_reaction_remove(reaction):
#     emoji = reaction.emoji
#     user = reaction.member
#     if user.bot:
#         return
#     if emoji.name == emoji_dict['sign_in'].split(":")[1]:
#         print("Someone signed out")
#     elif emoji.name == emoji_dict['bench'].split(":")[1]:
#         print("Someone stood up from the bench")
#     else:
#         return


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
    em = discord.Embed(title=f'Usage: {ctx.prefix}{cmd.name} {cmd.signature}', color=discord.Color.dark_gold())
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
