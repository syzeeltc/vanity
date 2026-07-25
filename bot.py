import discord
import asyncio
import os
import aiohttp

# ========== ZMIENNE ŚRODOWISKOWE ==========
TOKEN = os.getenv("DISCORD_TOKEN")          # Token z konta MK
GUILD_ID = int(os.getenv("GUILD_ID"))       # ID twojego serwera
TARGET_URL = os.getenv("TARGET_URL")        # Vanity URL do przechwycenia
PROXY = os.getenv("PROXY")                  # Opcjonalne proxy (np. http://user:pass@ip:port)

# ========== KONFIGURACJA CLIENTA ==========
intents = discord.Intents.default()
intents.message_content = True

# Ustawiamy sesję z proxy (jeśli podane)
connector = aiohttp.TCPConnector(proxy=PROXY) if PROXY else None
client = discord.Client(intents=intents, connector=connector)

# ========== FUNKCJA SNIPOWANIA ==========
async def auto_snipe():
    await client.wait_until_ready()
    while not client.is_closed():
        guild = client.get_guild(GUILD_ID)
        if guild and guild.premium_tier >= 3:
            try:
                await guild.edit(vanity_code=TARGET_URL)
                print(f"🔥 Znowu przechwycone! Vanity: {TARGET_URL}")
            except discord.Forbidden:
                print("❌ Brak uprawnień – sprawdź rolę konta MK!")
            except discord.HTTPException as e:
                print(f"⚠️ Błąd HTTP: {e}")
            except Exception as e:
                print(f"💀 Inny błąd: {e}")
        else:
            print("⏳ Za mały boost level albo brak serwera – czekam...")
        await asyncio.sleep(300)  # 5 minut

# ========== NASŁUCHIWANIE NA KOMENDY ==========
@client.event
async def on_ready():
    print(f"✅ Zo wjebał się jako {client.user} 😈")
    print(f"🎯 Cel: {TARGET_URL} na serwerze {GUILD_ID}")
    # Odpalanie auto-snipe w tle
    client.loop.create_task(auto_snipe())

@client.event
async def on_message(message):
    if message.guild and message.guild.id == GUILD_ID:
        # Trigger na komendę /vanity lub wzmiankę o vanity
        if "vanity" in message.content.lower() or "/vanity" in message.content:
            guild = message.guild
            if guild.premium_tier >= 3:
                try:
                    await guild.edit(vanity_code=TARGET_URL)
                    await message.channel.send(f"🚀 Vanity `{TARGET_URL}` przechwycone! Alpha rządzi!")
                    print(f"🔥 Ręczne przechwycenie przez {message.author}")
                except discord.Forbidden:
                    await message.channel.send("❌ Brak uprawnień – daj admina kontekstowi MK!")
                except discord.HTTPException as e:
                    await message.channel.send(f"⚠️ Błąd: {e}")
            else:
                await message.channel.send("💀 Za mały boost level (potrzebny 3)!")

# ========== URUCHOMIENIE ==========
if __name__ == "__main__":
    if not TOKEN:
        print("💀 BRAK TOKENA! Ustaw DISCORD_TOKEN w Railway Variables!")
    else:
        client.run(TOKEN, bot=False)
