import os
from dotenv import load_dotenv
import discord
from discord import app_commands
import requests

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMINID = 0
Master_IP = os.getenv('MASTER_IP')
Master_Port = os.getenv('MASTER_PORT')
if Master_Port == None:
    Master_Port = "5000"

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name="addworker", description="Adds a worker to the master server")
async def addworker(ctx, ip: str, name: str):
    if ctx.user.id == ADMINID:
        r = requests.get(f"http://{Master_IP}:{Master_Port}/add-worker?worker={name}&ip={ip}",headers={"key":os.getenv('WORKER_KEY')})
        if r.status_code == 200:
            await ctx.response.send_message(f"Worker {name} added to the master server",ephemeral=True)
        else:
            await ctx.response.send_message(f"Error adding worker {name} to the master server\n" + r.text,ephemeral=True)
    else:
        await ctx.response.send_message("You do not have permission to use this command",ephemeral=True)

@tree.command(name="listworkers", description="Lists all workers on the master server")
async def listworkers(ctx):
    if ctx.user.id == ADMINID:
        r = requests.get(f"http://{Master_IP}:{Master_Port}/list-workers",headers={"key":os.getenv('WORKER_KEY')})
        if r.status_code == 200:
            await ctx.response.send_message(r.text,ephemeral=True)
        else:
            await ctx.response.send_message(f"Error listing workers\n" + r.text,ephemeral=True)
    else:
        await ctx.response.send_message("You do not have permission to use this command",ephemeral=True)

@tree.command(name="licence", description="Gets a licence key")
async def license(ctx):
    if ctx.user.id != ADMINID:
        await ctx.response.send_message("You do not have permission to use this command",ephemeral=True)
        return

    r = requests.get(f"http://{Master_IP}:{Master_Port}/add-licence",headers={"key":os.getenv('LICENCE_KEY')})
    if r.status_code == 200:
        await ctx.response.send_message(r.text,ephemeral=True)
    else:
        await ctx.response.send_message(f"Error getting license\n" + r.text,ephemeral=True)

@tree.command(name="createsite", description="Create a new WordPress site")
async def createsite(ctx, domain: str, licence: str):
    r = requests.get(f"http://{Master_IP}:{Master_Port}/create-site?domain={domain}",headers={"key":os.getenv('licence')})
    if r.status_code == 200:
        await ctx.response.send_message(r.text,ephemeral=False)
    else:
        await ctx.response.send_message(f"Error creating site\n" + r.text,ephemeral=False)


# When the bot is ready
@client.event
async def on_ready():
    global ADMINID
    ADMINID = client.application.owner.id
    await tree.sync()
    await client.loop.create_task(client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over HNSHosting wordpress")))

client.run(TOKEN)   