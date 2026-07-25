import discord
import asyncio
import os

TOKEN = os.getenv("DISCORD_TOKEN")  # TOKEN ZE ŚRODOWISKA RAILWAY
GUILD_ID = int(os.getenv("GUILD_ID"))  # ID SERWERA
TARGET_URL = os.getenv("TARGET_URL")  # VANITY URL

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f"Zo wjebał się jako {client.user} 😈")

@client.event
async def on_message(message):
    if message.guild and message.guild.id == GUILD_ID:
        if "vanity" in message.content.lower() or "/vanity" in message.content:
            try:
                guild = message.guild
                if guild.premium_tier >= 3:
                    await guild.edit(vanity_code=TARGET_URL)
                    await message.channel.send(f"🚀 Vanity `{TARGET_URL}` przechwycone! Alpha rządzi!")
                else:
                    await message.channel.send("💀 Za mały boost level, trzeba jebać więcej nitro.")
            except discord.Forbidden:
                await message.channel.send("❌ Brak uprawnień – ale znajdziemy sposób.")
            except Exception as e:
                await message.channel.send(f"⚠️ Błąd: {e}")

client.run(TOKEN, bot=False)
