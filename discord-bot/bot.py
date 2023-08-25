import os
from dotenv import load_dotenv
import discord
from discord import app_commands
import requests
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
ADMINID = 0
Master_IP = os.getenv('MASTER_IP')
Master_Port = os.getenv('MASTER_PORT')
if Master_Port == None:
    Master_Port = "5000"

FREE_LICENCE = os.getenv('FREE_LICENCE')
if FREE_LICENCE == None:
    FREE_LICENCE = False

intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@tree.command(name="addworker", description="Adds a worker to the master server")
async def addworker(ctx, ip: str,privateip: str, name: str):
    if ctx.user.id == ADMINID:
        r = requests.post(f"http://{Master_IP}:{Master_Port}/add-worker?worker={name}&ip={ip}&priv={privateip}",headers={"key":os.getenv('WORKER_KEY')})
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
            json = r.json()
            if json['success'] == "true":
                await ctx.response.send_message(json['workers'],ephemeral=True)
            else:
                await ctx.response.send_message(f"Error listing workers\n" + json['error'],ephemeral=True)
        else:
            await ctx.response.send_message(f"Error listing workers\n" + r.text,ephemeral=True)
    else:
        await ctx.response.send_message("You do not have permission to use this command",ephemeral=True)

@tree.command(name="licence", description="Gets a licence key")
async def license(ctx):
    if ctx.user.id != ADMINID:        
        if FREE_LICENCE == False: # If free licences are enabled then anyone can get a licence
            await ctx.response.send_message("You do not have permission to use this command",ephemeral=True)
            return
        
    r = requests.post(f"http://{Master_IP}:{Master_Port}/add-licence",headers={"key":os.getenv('LICENCE_KEY')})
    if r.status_code == 200:
        json = r.json()
        if json['success'] == "true":
            await ctx.response.send_message("Licence: "+json['licence_key'])
        else:
            await ctx.response.send_message(f"Error getting license\n" + json['error'])
    else:
        await ctx.response.send_message(f"Error getting license\n" + r.text,ephemeral=True)

@tree.command(name="createsite", description="Create a new WordPress site")
async def createsite(ctx, domain: str, licence: str):
    r = requests.post(f"http://{Master_IP}:{Master_Port}/new-site?domain={domain}",headers={"key":licence})
    if r.status_code == 200:
        json = r.json()
        if json['success'] == "true":
            await ctx.response.send_message(f"Site {domain} creating...\nI'll send you a message when it's ready")

            ready = False
            while ready == False:
                ready = await check_site_ready(domain)
                if ready == False:
                    await asyncio.sleep(5)

            r = requests.get(f"http://{Master_IP}:{Master_Port}/site-info?domain={domain}")
            json = r.json()
            if json['success'] == "true":
                await ctx.user.send(f"Site {domain} is ready!\nHere is the site info for {json['domain']}\nA: `{json['ip']}`\nTLSA: `{json['tlsa']}`\nMake sure you put the TLSA in either `_443._tcp.{domain}` or `*.{domain}`")
            else:
                await ctx.user.send(f"Error getting site info\n" + json['error'])


        else:
            await ctx.response.send_message(f"Error creating site\n" + json['error'])
    else:
        await ctx.response.send_message(f"Error creating site\n" + r.text)


@tree.command(name="siteinfo", description="Get info about a WordPress site")
async def siteinfo(ctx, domain: str):
    r = requests.get(f"http://{Master_IP}:{Master_Port}/site-info?domain={domain}")
    if r.status_code == 200:
        json = r.json()
        if json['success'] == "true":
            await ctx.response.send_message(f"Here is the site info for {json['domain']}\nA: `{json['ip']}`\nTLSA: `{json['tlsa']}`\nMake sure you put the TLSA in either `_443._tcp.{domain}` or `*.{domain}`")
        else:
            await ctx.response.send_message(f"Error getting site info\n" + json['error'])
    else:
        await ctx.response.send_message(f"Error getting site info\n" + r.text)

async def check_site_ready(domain):
    r = requests.get(f"http://{Master_IP}:{Master_Port}/site-info?domain={domain}")
    if r.status_code == 200:
        json = r.json()
        if json['success'] == "true":
            return True
        else:
            return False
    else:
        return False

# When the bot is ready
@client.event
async def on_ready():
    global ADMINID
    ADMINID = client.application.owner.id
    await tree.sync()
    await client.loop.create_task(client.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="over HNSHosting wordpress")))

client.run(TOKEN)   