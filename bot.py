import requests
import os
import time
import discord
from discord.ext import commands
import asyncio

# ========== ZMIENNE ŚRODOWISKOWE ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")  # TOKEN BOTA (NIE TWÓJ!)
if not BOT_TOKEN:
    raise ValueError("💀 Ustaw BOT_TOKEN!")

GUILD_ID = os.getenv("GUILD_ID")
if not GUILD_ID:
    raise ValueError("💀 Ustaw GUILD_ID!")
GUILD_ID = int(GUILD_ID)

TARGET_URL = os.getenv("TARGET_URL")
if not TARGET_URL:
    raise ValueError("💀 Ustaw TARGET_URL!")

CHANNEL_ID = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    raise ValueError("💀 Ustaw CHANNEL_ID!")
CHANNEL_ID = int(CHANNEL_ID)

YOUR_USER_ID = os.getenv("YOUR_USER_ID")
if not YOUR_USER_ID:
    raise ValueError("💀 Ustaw YOUR_USER_ID!")
YOUR_USER_ID = int(YOUR_USER_ID)

# ========== KONFIGURACJA BOTA ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== SPRAWDZANIE VANITY ==========
def check_vanity():
    """Sprawdza czy vanity jest wolne (BEZ TOKENA!)"""
    # Używamy PUBLICZNEGO API Discorda – nie wymaga tokena!
    url = f"https://discord.com/api/v9/invites/{TARGET_URL}"
    
    try:
        r = requests.get(url)
        
        if r.status_code == 404:
            # 404 = link nie istnieje = vanity jest WOLNE!
            print(f"🔥 {TARGET_URL} JEST WOLNE!")
            return True, None
            
        elif r.status_code == 200:
            # 200 = link istnieje = jest zajęte
            data = r.json()
            guild_name = data.get("guild", {}).get("name", "Nieznany serwer")
            print(f"⏳ {TARGET_URL} jest ZAJĘTE przez: {guild_name}")
            return False, guild_name
            
        elif r.status_code == 429:
            print("⏳ Rate limit! Czekam 60 sekund...")
            time.sleep(60)
            return check_vanity()
            
        else:
            print(f"⚠️ Błąd {r.status_code}: {r.text}")
            return False, None
            
    except requests.exceptions.RequestException as e:
        print(f"💀 Błąd sieci: {e}")
        return False, None
    except Exception as e:
        print(f"💀 Nieznany błąd: {e}")
        return False, None

# ========== POWIADOMIENIA ==========
async def send_alert():
    """Wysyła powiadomienie na DM i kanał"""
    
    # DM do ciebie
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        if user:
            dm_channel = await user.create_dm()
            await dm_channel.send(
                f"🚨🚨🚨 **ALPHA! VANITY JEST WOLNE!** 🚨🚨🚨\n"
                f"🎯 **Cel:** `{TARGET_URL}`\n"
                f"🔗 **Link:** https://discord.gg/{TARGET_URL}\n"
                f"⚡ **Ustaw to ręcznie w ustawieniach serwera!**"
            )
            print("✅ DM wysłane!")
    except Exception as e:
        print(f"💀 Błąd DM: {e}")
    
    # Wiadomość na kanale
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(
                f"🚨🚨🚨 @everyone **VANITY JEST WOLNE!** 🚨🚨🚨\n"
                f"🎯 **Cel:** `{TARGET_URL}`\n"
                f"🔗 **Link:** https://discord.gg/{TARGET_URL}\n"
                f"<@{YOUR_USER_ID}> **USTAW TO TERAZ!**"
            )
            print("✅ Wiadomość na kanale wysłana!")
    except Exception as e:
        print(f"💀 Błąd kanału: {e}")

# ========== GŁÓWNA PĘTLA ==========
async def monitor_loop():
    await bot.wait_until_ready()
    print("🔍 Rozpoczynam monitorowanie (BEZ TWOJEGO TOKENA!)...")
    
    while not bot.is_closed():
        try:
            is_free, guild_name = check_vanity()
            
            if is_free:
                print(f"🔥🔥🔥 WOLNE! {TARGET_URL} JEST DOSTĘPNE! 🔥🔥🔥")
                await send_alert()
                # Po znalezieniu wolnego, czekamy dłużej (żeby nie spamować)
                await asyncio.sleep(3600)  # 1 godzina
            else:
                if guild_name:
                    print(f"⏳ Zajęte przez: {guild_name}")
                await asyncio.sleep(60)  # Sprawdzaj co minutę
                
        except Exception as e:
            print(f"💀 Błąd w pętli: {e}")
            await asyncio.sleep(60)

# ========== KOMENDY ==========
@bot.command()
async def vanity(ctx):
    """Sprawdza aktualny vanity URL"""
    is_free, guild_name = check_vanity()
    
    if is_free:
        await ctx.send(f"🔥🔥🔥 `{TARGET_URL}` JEST WOLNE! Ustaw to teraz!")
    else:
        await ctx.send(f"⏳ `{TARGET_URL}` jest ZAJĘTE przez: {guild_name}")

@bot.command()
async def ping(ctx):
    """Ping"""
    await ctx.send("🏓 Pong!")

# ========== URUCHOMIENIE ==========
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")
    print(f"🎯 Monitorowanie: {TARGET_URL}")
    print(f"📢 Kanał: {CHANNEL_ID}")
    print(f"👤 Powiadomienia dla: {YOUR_USER_ID}")
    print("=" * 50)
    bot.loop.create_task(monitor_loop())

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("💀 BRAK BOT_TOKEN!")
    else:
        bot.run(BOT_TOKEN)
