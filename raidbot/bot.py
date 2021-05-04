# bot.py
from datetime import datetime
import os
import random
import traceback
import asyncio

import discord
from discord.ext import commands
from pytz import timezone

from raidbot.event import make_event_from_db, Event
from raidbot.database import *
from raidbot.raidbuilder import make_character_from_db, Character, make_raid, JOBS
from raidbot.emoji_dict import emoji_dict

intents = discord.Intents().default()
intents.members = True
bot = commands.Bot(command_prefix='$', intents=intents)


def run(TOKEN):
    bot.run(TOKEN)


def job_emoji_str(job_list):
    emoji_str = ""
    for job in job_list:
        if job is not None:
            emoji_str += emoji_dict[job] + " "
    return emoji_str


def role_num_emoji_str(n_tanks, n_healers, n_dps):
    return f"{n_tanks} {emoji_dict['Tank']} {n_healers} {emoji_dict['Healer']} {n_dps} {emoji_dict['DPS']}"


def ping_string(list_of_ids):
    ping_str = "Hey, "
    for i in list_of_ids:
        ping_str += f"<@{i}>, "
    return ping_str[:-2]


def build_countdown_link(timestamp):
    dt_obj = datetime.fromtimestamp(timestamp, tz=timezone("UTC"))
    link = f"https://www.timeanddate.com/countdown/generic?iso={dt_obj.year}{dt_obj.month:02}{dt_obj.day:02}" \
           f"T{dt_obj.hour:02}{dt_obj.minute:02}{dt_obj.second:02}&p0=0&font=cursive"
    return link


@bot.event
async def on_ready():
    print(f'{bot.user.name} has connected to Discord!')


@bot.event
async def on_guild_join(guild):
    conn = create_connection(guild.id)
    initialize_db_with_tables(conn)
    conn.close()


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


@bot.command(name='set-event-channel', help='Sets the channel to post events in. '
                                            'Channel should be given with # and linked. '
                                            'Bot needs to be allowed to post in that channel. '
                                            'Can only be executed by admins.')
@commands.has_permissions(administrator=True)
async def set_event_channel(ctx, channel):
    if channel[0:2] != "<#":
        await ctx.send('Channel should be given with # and linked.')
        return

    channel_obj = bot.get_channel(int(channel[2:-1]))
    if not channel_obj:
        await ctx.send(f'Channel {channel} does not exist.')
        return
    if channel_obj.type.name != 'text':
        await ctx.send(f'Channel {channel} is not a text channel.')
        return
    req_permissions = discord.Permissions(2148001856)
    # Check discord developer portal for correct integer for permissions
    if not ctx.guild.me.permissions_in(channel_obj).is_superset(req_permissions):
        # if our bot does not have the required (or more) permissions in a channel
        await ctx.send(f'The bot does not have the required permissions in channel {channel}. '
                       f'Please set the correct permissions beforehand.')
        return
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        db_channel = get_server_info(conn, "event_channel")
        if db_channel:
            update_server_info(conn, "event_channel", channel)
        else:
            create_server_info(conn, "event_channel", channel)
        conn.close()
        await ctx.send(f"Channel {channel} is set as event_channel. All events will now be posted there.")
    else:
        await ctx.send('Could not connect to database.')


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
    embed.add_field(name="**Time**", value=f"[{ev.get_time()}]({build_countdown_link(ev.timestamp)})", inline=False)

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


@bot.command(name='show-event', help='Shows an event from the database given its id')
async def show_event(ctx, event_id):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        try:
            event = make_event_from_db(conn, event_id)
            embed = make_event_embed(event, ctx.guild)
            if event.message_link:
                embed.add_field(name="**Original post**", value=f"[link]({event.message_link})", inline=False)
            conn.close()
            await ctx.send(embed=embed)
        except Exception:
            conn.close()
            await ctx.send(f'Could not find event with id {event_id}. This event might not exist (yet).')
    else:
        await ctx.send('Could not connect to database.')


@bot.command(name='show-character', help='Shows characters registered with the given Discord ID')
async def show_character(ctx, discord_id):
    num_id = int(discord_id[3:-1])
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        try:  # TODO: handle multiple characters registered with the same discord id
            chara, date, num_raids = make_character_from_db(conn, num_id, None)
            embed = make_character_embed(chara, date, num_raids)
            conn.close()
            await ctx.send(f"<@{num_id}>'s character:", embed=embed)
        except Exception:
            conn.close()
            await ctx.send(f'Could not find character with id <@{num_id}>. This player might not be registered (yet).')
    else:
        await ctx.send('Could not connect to database.')


@bot.command(name='make-event', help='creates an event given parameters: '
                                     'name date (format d-m-y) time (format HH:MM) '
                                     'num_Tanks num_Heals num_DPS timezone (optional, default UTC)\n'
                                     '**Note:** Parameters are separated by spaces, so if you want a space in'
                                     'for eaxmple <name>, you need to put name in quotation marks like this:'
                                     ' "Event Name"')
async def make_event(ctx, name, date, start_time, num_tanks, num_heals, num_dps, user_timezone="UTC"):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        try:
            tz = timezone(user_timezone)
        except Exception:
            conn.close()
            tz_link = "https://gist.github.com/heyalexej/8bf688fd67d7199be4a1682b3eec7568"
            embed = discord.Embed(description=f"A link to all possible timezones can be found [here]({tz_link})",
                                  color=discord.Color.dark_gold())
            await ctx.send(f"Unknown timezone {user_timezone}, use format like 'Europe/Amsterdam'", embed=embed)
            return

        try:
            d, m, y = date.split("-")
            hour, minute = start_time.split(":")
            dt_obj = datetime(int(y), int(m), int(d), int(hour), int(minute))
            dt_obj = tz.normalize(tz.localize(dt_obj))
        except Exception:
            conn.close()
            await ctx.send(f"Could not parse date and/or time, make sure to format like this: "
                           f"dd-mm-yyyy hh:mm (in 24 hour format)")
            return

        event_tup = (name, int(dt_obj.timestamp()), None, None, None,
                     None, f"{num_tanks},{num_heals},{num_dps}",
                     int(ctx.message.author.id), None, "RECRUITING")
        ev_id = create_event(conn, event_tup)

        try:
            event = make_event_from_db(conn, ev_id)
        except Exception:
            conn.close()
            await ctx.send(f'Could not find event with id {ev_id}. This event might not exist (yet).')
            return
        embed = make_event_embed(event, ctx.guild, True)
        # Check if we have an event channel
        db_eventchannel = get_server_info(conn, "event_channel")
        if db_eventchannel:
            channel = db_eventchannel[0][2]
            message = await ctx.guild.get_channel(int(channel[2:-1])).send(embed=embed)
            new_embed = make_event_embed(event, ctx.guild, False)
            new_embed.add_field(name="**Original post**", value=f"[link]({message.jump_url})", inline=False)
            await ctx.send(embed=new_embed)
        else:
            message = await ctx.send(embed=embed)
        update_event(conn, "message_link", message.jump_url, ev_id)
        await message.add_reaction(emoji_dict["sign_in"])
        await message.add_reaction(emoji_dict["bench"])
        await message.add_reaction(emoji_dict["sign_out"])
        conn.close()
        return
    else:
        await ctx.send('Could not connect to database. Need connection to create and save events.')
        return


@bot.command(name='edit-event', help='Edits the given field of an event given its id. Only the event creator can edit. '
                                     'Field can be either name, date, or time. Time will always be assumed UTC '
                                     'which is Servertime.')
async def edit_event(ctx, ev_id, field, value):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        db_ev = get_event(conn, ev_id)
        if db_ev:
            event = make_event_from_db(conn, ev_id)
            if event.creator_id != ctx.message.author.id:
                conn.close()
                await ctx.send(f'You are not the author for this event. Only the author can edit events.')
                return
            if field == "name":
                update_event(conn, "name", value, event.id)
                link = event.message_link.split('/')
                message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                    int(link[-1]))
                event.name = value
                embed = make_event_embed(event, message.guild, True if event.state == "RECRUITING" else False)
                await message.edit(embed=embed)
                await ctx.send("Event name updated.")
                conn.close()
                await show_event(ctx, event.id)
                return
            elif field == "date":
                dt_object = datetime.fromtimestamp(event.timestamp)
                try:
                    d, m, y = value.split("-")
                    dt_object = dt_object.replace(day=int(d), month=int(m), year=int(y))
                except Exception:
                    conn.close()
                    await ctx.send(f"Could not parse date, make sure to format like this: "
                                   f"dd-mm-yyyy")
                    return
                timestamp = int(dt_object.timestamp())
                update_event(conn, "timestamp", timestamp, event.id)
                link = event.message_link.split('/')
                message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                    int(link[-1]))
                event.timestamp = timestamp
                embed = make_event_embed(event, message.guild, True if event.state == "RECRUITING" else False)
                await message.edit(embed=embed)
                await ctx.send("Event date updated.")
                conn.close()
                await show_event(ctx, event.id)
                return

            elif field == "time":
                dt_object = datetime.fromtimestamp(event.timestamp)
                try:
                    hour, minute = value.split(":")
                    dt_object = dt_object.replace(hour=int(hour), minute=int(minute))
                except Exception:
                    conn.close()
                    await ctx.send(f"Could not parse time, make sure to format like this: "
                                   f"hh:mm (in 24 hour format)")
                    return
                timestamp = int(dt_object.timestamp())
                update_event(conn, "timestamp", timestamp, event.id)
                link = event.message_link.split('/')
                message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                    int(link[-1]))
                event.timestamp = timestamp
                embed = make_event_embed(event, message.guild, True if event.state == "RECRUITING" else False)
                await message.edit(embed=embed)
                await ctx.send("Event time updated.")
                await show_event(ctx, event.id)
                conn.close()
                return
            else:
                conn.close()
                await ctx.send(f'{field} is not an editable field.\n'
                               f'Editable fields are "name", "date", or "time"')
                return
        else:
            conn.close()
            await ctx.send(f'There is no event with id {ev_id}.')
            return
    else:
        await ctx.send('Could not connect to database.')
        return


@bot.command(name='close-event', help='closes recruitment for an event. Will ask you to decide on the composition'
                                      'via DM. Needs the event ID.')
async def close_event(ctx, ev_id):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        db_ev = get_event(conn, ev_id)
        if db_ev:
            event = make_event_from_db(conn, ev_id)
            # Check if we have an event channel
            db_eventchannel = get_server_info(conn, "event_channel")
            if db_eventchannel:
                channel_tag = db_eventchannel[0][2]
                channel = ctx.guild.get_channel(int(channel_tag[2:-1]))
            else:
                channel = ctx
            if event.creator_id != ctx.message.author.id:
                conn.close()
                await ctx.send(f'You are not the author for this event. Only the author can close events.')
                return
            if event.state != "RECRUITING":
                conn.close()
                await ctx.send(f'This event has already been closed.')
                return
            if len(event.participant_ids) < sum(event.role_numbers):
                await ctx.message.author.send(f'There are not enough participants registered for this event. '
                                              f'You can either CANCEL the event, or call on all registered participants '
                                              f'for an UNDERSIZED event in which you fill up with Party Finder. \n'
                                              f'`1` - CANCEL event\n'
                                              f'`2` - UNDERSIZED event\n'
                                              f'`esc` - stop closing dialogue')

                def check(m):
                    return ctx.message.author == m.author \
                           and (m.content == "1" or m.content == "2" or m.content == "esc") \
                           and not m.guild
                # await response
                try:
                    msg = await bot.wait_for('message', check=check, timeout=3600.0)
                except asyncio.TimeoutError:
                    conn.close()
                    await ctx.message.author.send(f'Stopping $close-event dialogue due to timeout.')
                    return
                else:
                    if msg.content == "1":
                        await ctx.message.author.send(f'you have decided to CANCEL the event.')
                        link = event.message_link.split('/')
                        message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                            int(link[-1]))
                        event.state = "CANCELLED"
                        update_event(conn, "state", event.state, event.id)
                        embed = make_event_embed(event, message.guild, False)
                        await message.edit(embed=embed)
                        for em in [emoji_dict["sign_in"], emoji_dict["sign_out"], emoji_dict["bench"]]:
                            await message.remove_reaction(em, bot.user)
                        new_emb = discord.Embed(title=f"**Event {event.id} - {event.name}**",
                                                description=f"Has been **CANCELLED**",
                                                color=discord.Color.dark_gold())
                        await channel.send(embed=new_emb)
                    elif msg.content == "2":
                        await ctx.message.author.send(f'you have decided to run the event UNDERSIZED.')
                        link = event.message_link.split('/')
                        message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                            int(link[-1]))
                        event.state = "UNDERSIZED"
                        update_event(conn, "state", event.state, event.id)
                        # all benched will need to participate
                        for i, _ in enumerate(event.is_bench):
                            event.is_bench[i] = 0
                        update_event(conn, "is_bench", col_str(event.is_bench), event.id)
                        # Jobs need to be figured out on their own, pf can fill anything right?
                        embed = make_event_embed(event, message.guild, False)
                        await message.edit(embed=embed)
                        for em in [emoji_dict["sign_in"], emoji_dict["sign_out"], emoji_dict["bench"]]:
                            await message.remove_reaction(em, bot.user)
                        new_emb = discord.Embed(title=f"**Event {event.id} - {event.name}**",
                                                description=f"will be run **UNDERSIZED**",
                                                color=discord.Color.dark_gold())
                        new_emb.add_field(name="**Time**",
                                          value=f"[{event.get_time()}]({build_countdown_link(event.timestamp)})",
                                          inline=False)
                        signed_str, _ = event.signed_in_and_benched_as_strs()
                        if signed_str:
                            new_emb.add_field(name="**Participants**", value=signed_str, inline=False)
                        await channel.send(ping_string(event.participant_ids), embed=new_emb)
                    elif msg.content == "esc":
                        await ctx.message.author.send(f'Stopping $close-event dialogue.')
                conn.close()
                return
            else:
                # THIS IS WHERE THE MAGIC HAPPENS!
                # Get Information from event
                participants = []
                num_raids = []
                for i, p_id in enumerate(event.participant_ids):
                    chara, _, n_raid = make_character_from_db(conn, p_id, event.participant_names[i])
                    if event.is_bench[i]:
                        chara.benched = True
                    participants.append(chara)
                    num_raids.append(n_raid)

                await ctx.message.author.send(f'Building a group for event {event.id} ...')
                # Get X best raids
                best_raids = make_raid(participants, event.role_numbers[0], event.role_numbers[1], event.role_numbers[2])
                if not best_raids:
                    # No viable combination was found
                    await ctx.message.author.send(f"I could not create a viable group given the participants' jobs and "
                                                  f"the expected roles for this event.")
                    await ctx.message.author.send(f'You can either CANCEL the event, or call on all registered participants '
                                                  f'for a MANUAL event in which you build the party yourself with other jobs or pf. \n'
                                                  f'`1` - CANCEL event\n'
                                                  f'`2` - MANUAL event\n'
                                                  f'`esc` - stop closing dialogue')

                    def check(m):
                        return ctx.message.author == m.author \
                               and (m.content == "1" or m.content == "2" or m.content == "esc") \
                               and not m.guild

                    # await response
                    try:
                        msg = await bot.wait_for('message', check=check, timeout=3600.0)
                    except asyncio.TimeoutError:
                        conn.close()
                        await ctx.message.author.send(f'Stopping $close-event dialogue due to timeout.')
                        return
                    else:
                        if msg.content == "1":
                            await ctx.message.author.send(f'you have decided to CANCEL the event.')
                            link = event.message_link.split('/')
                            message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                                int(link[-1]))
                            event.state = "CANCELLED"
                            update_event(conn, "state", event.state, event.id)
                            embed = make_event_embed(event, message.guild, False)
                            await message.edit(embed=embed)
                            for em in [emoji_dict["sign_in"], emoji_dict["sign_out"], emoji_dict["bench"]]:
                                await message.remove_reaction(em, bot.user)
                            new_emb = discord.Embed(title=f"**Event {event.id} - {event.name}**",
                                                    description=f"Has been **CANCELLED**",
                                                    color=discord.Color.dark_gold())
                            await channel.send(embed=new_emb)
                        elif msg.content == "2":
                            await ctx.message.author.send(f'you have decided to run the event MANUAL.')
                            link = event.message_link.split('/')
                            message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                                int(link[-1]))
                            event.state = "MANUAL"
                            update_event(conn, "state", event.state, event.id)
                            # Jobs need to be figured out on their own, pf can fill anything right?
                            embed = make_event_embed(event, message.guild, False)
                            await message.edit(embed=embed)
                            for em in [emoji_dict["sign_in"], emoji_dict["sign_out"], emoji_dict["bench"]]:
                                await message.remove_reaction(em, bot.user)
                            new_emb = discord.Embed(title=f"**Event {event.id} - {event.name}**",
                                                    description=f"will be run **MANUAL**",
                                                    color=discord.Color.dark_gold())
                            new_emb.add_field(name="**Time**",
                                              value=f"[{event.get_time()}]({build_countdown_link(event.timestamp)})",
                                              inline=False)
                            signed_str, bench_str = event.signed_in_and_benched_as_strs()
                            if signed_str:
                                new_emb.add_field(name="**Participants**", value=signed_str, inline=False)
                            if bench_str:
                                new_emb.add_field(name="**On the bench**", value=bench_str, inline=False)
                            await channel.send(embed=new_emb)
                        elif msg.content == "esc":
                            await ctx.message.author.send(f'Stopping $close-event dialogue.')
                    conn.close()
                    return

                # We have at least 1 working combo
                combo_str = ""
                for i, (group, comp, score) in enumerate(best_raids):
                    curr_str = ""
                    for player in group:
                        job = comp[group.index(player)]
                        curr_str += f"{emoji_dict[job]} {player.character_name}, "
                    combo_str += f"`{i}` - " + curr_str[:-2] + "\n"

                combo_str += "`rnd` -  choose one of the above at random."

                new_emb = discord.Embed(title=f"Best Combinations:",
                                        description=combo_str,
                                        color=discord.Color.dark_gold())
                await ctx.message.author.send("Please choose a composition out of the following:", embed=new_emb)

                def check(m):
                    return ctx.message.author == m.author \
                           and not m.guild \
                           and (m.content == "rnd" or int(m.content) in range(len(best_raids)))
                # await response
                try:
                    msg = await bot.wait_for('message', check=check, timeout=3600.0)
                except asyncio.TimeoutError:
                    conn.close()
                    await ctx.message.author.send(f'Stopping $close-event dialogue due to timeout.')
                    return
                except Exception:
                    conn.close()
                    await ctx.message.author.send(f'You sent something I cannot convert to a number. '
                                                  f'I cannot deal with this so you will have to '
                                                  f'restart the closing process.')
                    return
                else:
                    if msg.content == "rnd":
                        raidnum = random.randint(0, len(best_raids)-1)
                    else:
                        raidnum = int(msg.content)

                    group, comp, score = best_raids[raidnum]
                    # Update bench and jobs
                    for i, player in enumerate(participants):
                        if player in group:
                            event.is_bench[i] = 0
                            job = comp[group.index(player)]
                            event.jobs.append(job)
                            # Players num_raids ++
                            update_player(conn, "num_raids", num_raids[i] + 1,
                                          player.discord_id, player.character_name)
                        else:
                            if event.is_bench[i] == 0:
                                # Player did not want to be benched, involuntary benches ++
                                update_player(conn, "involuntary_benches", player.involuntary_benches + 1,
                                              player.discord_id, player.character_name)

                            event.is_bench[i] = 1
                            event.jobs.append(None)
                    # Sort lists according to FF sorting
                    job_inds = [JOBS.index(j) if j else float('Inf') for j in event.jobs]
                    new_inds = [i[0] for i in sorted(enumerate(job_inds), key=lambda x:x[1])]

                    event.participant_ids = [event.participant_ids[i] for i in new_inds]
                    update_event(conn, "participant_ids", col_str(event.participant_ids), event.id)
                    event.participant_names = [event.participant_names[i] for i in new_inds]
                    update_event(conn, "participant_names", col_str(event.participant_names), event.id)
                    event.jobs = [event.jobs[i] for i in new_inds]
                    update_event(conn, "jobs", col_str(event.jobs), event.id)
                    event.is_bench = [event.is_bench[i] for i in new_inds]
                    update_event(conn, "is_bench", col_str(event.is_bench), event.id)

                    # Edit Event post and make message
                    link = event.message_link.split('/')
                    message = await bot.get_guild(int(link[-3])).get_channel(int(link[-2])).fetch_message(
                        int(link[-1]))
                    event.state = "COMPLETE"
                    update_event(conn, "state", event.state, event.id)
                    embed = make_event_embed(event, message.guild, False)
                    await message.edit(embed=embed)
                    for em in [emoji_dict["sign_in"], emoji_dict["sign_out"], emoji_dict["bench"]]:
                        await message.remove_reaction(em, bot.user)
                    new_emb = discord.Embed(title=f"**Event {event.id} - {event.name}**",
                                            description=f"Recruitment has ended.",
                                            color=discord.Color.dark_gold())
                    # Get participants with their jobs
                    part_str = ""
                    for j, p_id in enumerate(event.participant_ids):
                        if event.is_bench[j] == 0:
                            part_str += f"{emoji_dict[event.jobs[j]]} {event.participant_names[j]}\n"
                    new_emb.add_field(name="**Participants**", value=part_str, inline=False)
                    # if event.jobs:
                    #     new_emb.add_field(name="**Jobs**", value=job_emoji_str(event.jobs), inline=False)
                    non_benched_ids = [p_id for j, p_id in enumerate(event.participant_ids) if not event.is_bench[j]]
                    await channel.send(ping_string(non_benched_ids), embed=new_emb)
                    conn.close()
                    await ctx.message.author.send(f'You have set the event and participants.')
                    return

        else:
            conn.close()
            await ctx.send(f'There is no event with id {ev_id}.')
            return
    else:
        await ctx.send('Could not connect to database.')
        return


@bot.command(name='register-character', help='Registers a character given parameters: name ("Firstname Lastname") '
                                             'job_list (formatted like "JOB,JOB,JOB", given in order of your priority)\n'
                                             '**Note:** Parameters are separated by spaces, so if you want a space '
                                             'in your name, you need to put name in quotation marks like this:'
                                             ' "Firstname Lastname"')
async def register_character(ctx, name, job_list):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, date, num_raids = make_character_from_db(conn, disc_id, None)
            embed = make_character_embed(chara, date, num_raids)
            conn.close()
            await ctx.send(f"There is already a character registered by <@{disc_id}>, "
                           f"multiple characters are not supported (yet).", embed=embed)
            return
        try:
            chara = Character(disc_id, name, job_list, 0)
            player = (chara.discord_id, name, job_list, datetime.today().strftime('%Y-%m-%d'), 0, 0)
            create_player(conn, player)
            embed = make_character_embed(chara, player[3], player[4])
            await ctx.send(f"<@{chara.discord_id}>'s character:", embed=embed)
        except Exception:
            conn.close()
            await ctx.send('Could not parse name and/or job list. '
                           'Format like this: `$register-character "Firstname Lastname" "JOB,JOB,JOB"`')
            return

    else:
        await ctx.send('Could not connect to database. Need connection to create and save characters.')
        return


@bot.command(name='delete-character', help='Deletes the character registered with your discord id.')
async def delete_character(ctx):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, _, _ = make_character_from_db(conn, disc_id, None)
            delete_player(conn, disc_id, chara.character_name)
            conn.close()
            await ctx.send(f'Character **{chara.character_name}** by <@{disc_id}> is now deleted.')
            return
        else:
            conn.close()
            await ctx.send(f'There is no character registered by <@{disc_id}> to delete.')
            return
    else:
        await ctx.send('Could not connect to database. Need connection to delete characters.')
        return


@bot.command(name='add-job', help="adds given job at given position in your character's job list. "
                                  "Pos 0 is in front of 1st job, pos 1 in front of 2nd job etc.")
async def add_job(ctx, job, pos):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, date, num_raids = make_character_from_db(conn, disc_id, None)
            job_list = chara.jobs
            try:
                job_list.insert(int(pos), job.upper())
            except Exception:
                conn.close()
                await ctx.send(f'Could not parse position. '
                               f'Position needs to be a valid insertion number for your job list.')
                return
            try:
                chara.set_jobs(job_list)
            except SyntaxError as e:
                conn.close()
                await ctx.send(f'Could not add job. {e.msg}.')
                return
            update_player(conn, "jobs", col_str(chara.jobs), disc_id, chara.character_name)
            embed = make_character_embed(chara, date, num_raids)
            conn.close()
            await ctx.send(f"<@{chara.discord_id}>'s character:", embed=embed)
            return
        else:
            conn.close()
            await ctx.send(f'There is no character registered by <@{disc_id}> to add jobs to.')
            return
    else:
        await ctx.send('Could not connect to database. Need connection to edit characters.')
        return


@bot.command(name='remove-job', help="removes the given job from your character's job list.")
async def remove_job(ctx, job):
    conn = create_connection(ctx.guild.id)
    if conn is not None:
        disc_id = ctx.message.author.id
        db_chara = get_player_by_id(conn, disc_id)
        if db_chara:
            chara, date, num_raids = make_character_from_db(conn, disc_id, None)
            try:
                chara.jobs.remove(job.upper())
            except ValueError:
                conn.close()
                await ctx.send(f'Job {job.upper()} is not in your job list.')
                return

            update_player(conn, "jobs", col_str(chara.jobs), disc_id, chara.character_name)
            embed = make_character_embed(chara, date, num_raids)
            conn.close()
            await ctx.send(f"<@{chara.discord_id}>'s character:", embed=embed)
            return
        else:
            conn.close()
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
        conn = create_connection(reaction.guild_id)
        if conn is not None:
            db_ev = find_events(conn, "message_link", message.jump_url)
            if not db_ev:
                # Reaction was not on an event post
                conn.close()
                return
            event = Event(*db_ev[0])
            if event.state != "RECRUITING":
                await user.send(f'You are trying to sign in/out for Event {event.id}, '
                                f'but the recruitment has ended.')
                conn.close()
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
                    # await user.send(f'You are now signed out of {event.id}!')
                    conn.close()
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
                        conn.close()
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
                        conn.close()
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
                        conn.close()
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
                    # await user.send(f'You are now signed in for {event.id}!')
                    conn.close()
                    await message.remove_reaction(emoji, user)
                    return

            # await user.send(f'You are trying to sign in to Event {event.id}!')
            conn.close()
            await message.remove_reaction(emoji, user)
            return
        else:
            await message.remove_reaction(emoji, user)
            await user.send('Could not connect to database to process you signing in. '
                            'Please contact an admin for this bot.')
            return
    else:
        return


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
