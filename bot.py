# bot.py
import os
import random

import discord
from discord.ext import commands
from dotenv import load_dotenv

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


bot.run(TOKEN)
