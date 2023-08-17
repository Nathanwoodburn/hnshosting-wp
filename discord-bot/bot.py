import os
from dotenv import load_dotenv
import discord
from discord import app_commands
import requests

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMINID = 0
Master_IP = os.getenv('MASTER_IP')

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name="addworker", description="Adds a worker to the master server")
async def addworker(ctx, ip: str, name: str):
    if ctx.author.id == ADMINID:
        r = requests.get(f"http://{Master_IP}:5000/add-worker?worker={name}&ip={ip}")
        if r.status_code == 200:
            await ctx.response.send_message(f"Worker {name} added to the master server",ephemeral=True)
        else:
            await ctx.response.send_message(f"Error adding worker {name} to the master server\n" + r.text,ephemeral=True)
    else:
        await ctx.response.send_message("You do not have permission to use this command",ephemeral=True)

   

# When the bot is ready
@client.event
async def on_ready():
    global ADMINID
    ADMINID = client.application.owner.id
    await tree.sync()
    await client.loop.create_task(client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over HNSHosting wordpress")))

client.run(TOKEN)