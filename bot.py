import requests
import os
import time
import discord
from discord.ext import commands
import asyncio

# ========== ZMIENNE ŚRODOWISKOWE ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
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
    """Sprawdza czy vanity jest wolne (z obsługą zbanowanych)"""
    url = f"https://discord.com/api/v9/invites/{TARGET_URL}"
    
    try:
        r = requests.get(url)
        
        # ===== 404 =====
        if r.status_code == 404:
            # Sprawdzamy treść błędu
            try:
                error_data = r.json()
                error_msg = error_data.get("message", "").lower()
                error_code = error_data.get("code", 0)
                
                # Jeśli błąd mówi o "invalid invite" lub "banned" -> jest zbanowana
                if "invalid" in error_msg or "banned" in error_msg or "suspended" in error_msg or "restricted" in error_msg:
                    print(f"🚫 VANITY {TARGET_URL} JEST ZBANOWANA/ZABRONIONA!")
                    return "BANNED", None
                else:
                    # 404 bez komunikatu o ban = może być wolna
                    # ALE nie jesteśmy pewni – lepiej traktować jako "niepewne"
                    print(f"⚠️ 404 dla {TARGET_URL} – ale nie wiemy czy to ban czy wolne")
                    return "UNKNOWN", None
                    
            except:
                print(f"⚠️ 404 bez JSON – traktuję jako wolne (ryzyko)")
                return "FREE", None
        
        # ===== 200 =====
        elif r.status_code == 200:
            data = r.json()
            guild_name = data.get("guild", {}).get("name", "Nieznany serwer")
            print(f"⏳ {TARGET_URL} jest ZAJĘTE przez: {guild_name}")
            return "TAKEN", guild_name
        
        # ===== 429 =====
        elif r.status_code == 429:
            print("⏳ Rate limit! Czekam 60 sekund...")
            time.sleep(60)
            return check_vanity()
        
        # ===== 403 =====
        elif r.status_code == 403:
            print("🚫 VANITY JEST ZBANOWANE LUB ZABRONIONE (403)!")
            return "BANNED", None
        
        # ===== INNE =====
        else:
            print(f"⚠️ Błąd {r.status_code}: {r.text}")
            return "UNKNOWN", None
            
    except requests.exceptions.RequestException as e:
        print(f"💀 Błąd sieci: {e}")
        return "UNKNOWN", None
    except Exception as e:
        print(f"💀 Nieznany błąd: {e}")
        return "UNKNOWN", None

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
                f"⚡ **SPRAWDŹ RĘCZNIE – MOŻE BYĆ BAN!**"
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
                f"<@{YOUR_USER_ID}> **SPRAWDŹ RĘCZNIE!**"
            )
            print("✅ Wiadomość na kanale wysłana!")
    except Exception as e:
        print(f"💀 Błąd kanału: {e}")

async def send_banned_alert():
    """Wysyła powiadomienie o zbanowanej vanity"""
    
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        if user:
            dm_channel = await user.create_dm()
            await dm_channel.send(
                f"🚫🚫🚫 **ALPHA! VANITY JEST ZBANOWANA!** 🚫🚫🚫\n"
                f"🎯 **Cel:** `{TARGET_URL}`\n"
                f"⏳ **Nie można jej użyć – czekaj na odbanowanie!**"
            )
            print("✅ DM o banie wysłane!")
    except Exception as e:
        print(f"💀 Błąd DM: {e}")

# ========== GŁÓWNA PĘTLA ==========
async def monitor_loop():
    await bot.wait_until_ready()
    print("🔍 Rozpoczynam monitorowanie...")
    print(f"🎯 Cel: {TARGET_URL}")
    print("=" * 50)
    
    while not bot.is_closed():
        try:
            status, guild_name = check_vanity()
            
            if status == "FREE":
                print(f"🔥🔥🔥 WOLNE! {TARGET_URL} JEST DOSTĘPNE! 🔥🔥🔥")
                await send_alert()
                await asyncio.sleep(3600)  # 1 godzina
                
            elif status == "BANNED":
                print(f"🚫 ZBANOWANE! {TARGET_URL} jest zablokowane przez Discord.")
                await send_banned_alert()
                await asyncio.sleep(3600)  # 1 godzina (żeby nie spamować)
                
            elif status == "TAKEN":
                print(f"⏳ Zajęte przez: {guild_name}")
                await asyncio.sleep(60)
                
            elif status == "UNKNOWN":
                print(f"⚠️ Nieznany status – czekam 5 minut...")
                await asyncio.sleep(300)
                
            else:
                print(f"⚠️ Nieznany status: {status}")
                await asyncio.sleep(60)
                
        except Exception as e:
            print(f"💀 Błąd w pętli: {e}")
            await asyncio.sleep(60)

# ========== KOMENDY ==========
@bot.command()
async def vanity(ctx):
    """Sprawdza aktualny status vanity"""
    status, guild_name = check_vanity()
    
    if status == "FREE":
        await ctx.send(f"🔥🔥🔥 `{TARGET_URL}` JEST WOLNE! Sprawdź ręcznie!")
    elif status == "BANNED":
        await ctx.send(f"🚫 `{TARGET_URL}` JEST ZBANOWANE/ZABRONIONE!")
    elif status == "TAKEN":
        await ctx.send(f"⏳ `{TARGET_URL}` jest ZAJĘTE przez: {guild_name}")
    else:
        await ctx.send(f"⚠️ Nieznany status: {status}")

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
