import requests
import os
import time
import discord
from discord.ext import commands
import asyncio
import json

# ========== ZMIENNE ŚRODOWISKOWE ==========
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("💀 Ustaw BOT_TOKEN!")

GUILD_ID = os.getenv("GUILD_ID")
if not GUILD_ID:
    raise ValueError("💀 Ustaw GUILD_ID!")
GUILD_ID = int(GUILD_ID)

CHANNEL_ID = os.getenv("CHANNEL_ID")
if not CHANNEL_ID:
    raise ValueError("💀 Ustaw CHANNEL_ID!")
CHANNEL_ID = int(CHANNEL_ID)

YOUR_USER_ID = os.getenv("YOUR_USER_ID")
if not YOUR_USER_ID:
    raise ValueError("💀 Ustaw YOUR_USER_ID!")
YOUR_USER_ID = int(YOUR_USER_ID)

# ========== LISTA VANITEK ==========
TARGET_URLS = [
    "wymianakasy",
    "wymieniano",
    "wymienwalute"
]

# ========== CZARNA LISTA ==========
BLACKLIST = [
    "wymieniano",
    "wymienwalute"
]

# ========== PAMIĘĆ STATUSÓW ==========
last_known_status = {}
already_notified = {}  # <---- NOWA FLAGA!

# ========== KONFIGURACJA BOTA ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== SPRAWDZANIE JEDNEJ VANITY ==========
def check_single_vanity(vanity_name):
    if vanity_name in BLACKLIST:
        return "BLACKLISTED", None
    
    url = f"https://discord.com/api/v9/invites/{vanity_name}"
    
    try:
        r = requests.get(url)
        
        if r.status_code == 200:
            data = r.json()
            guild_name = data.get("guild", {}).get("name", "Nieznany serwer")
            guild_id = data.get("guild", {}).get("id")
            
            if guild_id and int(guild_id) == GUILD_ID:
                return "OWN_SERVER", guild_name
            else:
                return "TAKEN", guild_name
        
        elif r.status_code == 404:
            return "FREE", None
        
        elif r.status_code == 429:
            print(f"⏳ Rate limit dla {vanity_name}, czekam 60s...")
            time.sleep(60)
            return check_single_vanity(vanity_name)
        
        elif r.status_code == 403:
            return "BANNED", None
        
        else:
            return "UNKNOWN", None
            
    except Exception as e:
        print(f"💀 Błąd sprawdzania {vanity_name}: {e}")
        return "UNKNOWN", None

# ========== SPRAWDZANIE WSZYSTKICH ==========
def check_all_vanities():
    results = {}
    for vanity in TARGET_URLS:
        status, guild_name = check_single_vanity(vanity)
        results[vanity] = {"status": status, "guild_name": guild_name}
        print(f"📊 {vanity}: {status}" + (f" ({guild_name})" if guild_name else ""))
    return results

# ========== POWIADOMIENIA ==========
async def send_vanity_alert(vanity_name):
    title = "🚨🚨🚨 WOLNE!"
    emoji = "🔥"
    message = f"🎯 **Vanity:** `{vanity_name}`\n🔗 **Link:** https://discord.gg/{vanity_name}\n⚡ **USTAW TO TERAZ!**"
    
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        if user:
            dm_channel = await user.create_dm()
            await dm_channel.send(f"{emoji}{emoji}{emoji} **{title}** {emoji}{emoji}{emoji}\n{message}")
            print(f"✅ DM dla {vanity_name} wysłane!")
    except Exception as e:
        print(f"💀 Błąd DM ({vanity_name}): {e}")
    
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"{emoji}{emoji}{emoji} @everyone **{title}** {emoji}{emoji}{emoji}\n{message}\n<@{YOUR_USER_ID}>")
            print(f"✅ Wiadomość na kanale ({vanity_name}) wysłana!")
    except Exception as e:
        print(f"💀 Błąd kanału ({vanity_name}): {e}")

# ========== KOMENDY ==========
@bot.command(name="vanity")
async def vanity_cmd(ctx):
    results = check_all_vanities()
    message = "📊 **STATUS VANITEK:**\n"
    
    for vanity_name, data in results.items():
        status = data["status"]
        if status == "FREE":
            emoji = "🔥"
        elif status == "BANNED":
            emoji = "🚫"
        elif status == "TAKEN":
            emoji = "⏳"
        elif status == "OWN_SERVER":
            emoji = "✅"
        elif status == "BLACKLISTED":
            emoji = "🚫"
        else:
            emoji = "⚠️"
        message += f"{emoji} `{vanity_name}`: {status}\n"
    
    await ctx.send(message)

@bot.command(name="check")
async def check_cmd(ctx, *, vanity_name: str = None):
    if not vanity_name:
        await ctx.send("❌ Podaj nazwę vanity! np. `!check wymianakasy`")
        return
    
    status, guild_name = check_single_vanity(vanity_name)
    
    if status == "FREE":
        await ctx.send(f"🔥 `{vanity_name}` JEST WOLNE!")
    elif status == "BANNED":
        await ctx.send(f"🚫 `{vanity_name}` JEST ZBANOWANE!")
    elif status == "TAKEN":
        await ctx.send(f"⏳ `{vanity_name}` jest ZAJĘTE przez: {guild_name}")
    elif status == "OWN_SERVER":
        await ctx.send(f"✅ `{vanity_name}` należy do TWOJEGO serwera!")
    elif status == "BLACKLISTED":
        await ctx.send(f"🚫 `{vanity_name}` jest na CZARNEJ LIŚCIE (ztermowane)")
    else:
        await ctx.send(f"⚠️ Nieznany status: {status}")

@bot.command(name="blacklist")
async def blacklist_cmd(ctx, *, vanity_name: str = None):
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if not vanity_name:
        current = "📋 **CZARNA LISTA:**\n"
        if BLACKLIST:
            for v in BLACKLIST:
                current += f"🚫 `{v}`\n"
        else:
            current += "✅ Pusto!"
        await ctx.send(current)
        return
    
    if vanity_name in BLACKLIST:
        BLACKLIST.remove(vanity_name)
        await ctx.send(f"✅ Usunięto `{vanity_name}` z czarnej listy!")
    else:
        BLACKLIST.append(vanity_name)
        await ctx.send(f"✅ Dodano `{vanity_name}` do czarnej listy!")

@bot.command(name="add")
async def add_cmd(ctx, *, vanity_name: str = None):
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if not vanity_name:
        await ctx.send("❌ Podaj nazwę vanity! np. `!add wymianakasy`")
        return
    
    if vanity_name in TARGET_URLS:
        await ctx.send(f"⚠️ `{vanity_name}` już jest na liście!")
    else:
        TARGET_URLS.append(vanity_name)
        await ctx.send(f"✅ Dodano `{vanity_name}` do monitorowania!")

@bot.command(name="remove")
async def remove_cmd(ctx, *, vanity_name: str = None):
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if not vanity_name:
        await ctx.send("❌ Podaj nazwę vanity! np. `!remove wymianakasy`")
        return
    
    if vanity_name not in TARGET_URLS:
        await ctx.send(f"⚠️ `{vanity_name}` nie ma na liście!")
    else:
        TARGET_URLS.remove(vanity_name)
        await ctx.send(f"✅ Usunięto `{vanity_name}` z monitorowania!")

@bot.command(name="list")
async def list_cmd(ctx):
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if not TARGET_URLS:
        await ctx.send("📋 Lista jest pusta!")
        return
    
    message = "📋 **MONITOROWANE VANITKI:**\n"
    for i, vanity_name in enumerate(TARGET_URLS, 1):
        banned = "🚫 " if vanity_name in BLACKLIST else ""
        message += f"{i}. {banned}`{vanity_name}`\n"
    
    await ctx.send(message)

@bot.command(name="ping")
async def ping_cmd(ctx):
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

@bot.command(name="reset")
async def reset_cmd(ctx):
    """Resetuje flagi powiadomień (tylko Alpha)"""
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    global already_notified
    already_notified = {}
    await ctx.send("✅ Zresetowano flagi powiadomień!")

# ========== GŁÓWNA PĘTLA MONITOROWANIA ==========
async def monitor_loop():
    await bot.wait_until_ready()
    print("🔍 Rozpoczynam monitorowanie WIELU VANITEK...")
    print(f"🎯 Liczba vanitek: {len(TARGET_URLS)}")
    print(f"🚫 Czarna lista: {BLACKLIST if BLACKLIST else 'Pusto'}")
    print("=" * 50)
    
    check_all_vanities()
    
    while not bot.is_closed():
        try:
            print(f"\n📊 Sprawdzanie {len(TARGET_URLS)} vanitek...")
            results = check_all_vanities()
            
            for vanity_name, data in results.items():
                status = data["status"]
                previous = last_known_status.get(vanity_name, {}).get("status")
                was_notified = already_notified.get(vanity_name, False)
                
                # Jeśli vanity jest na czarnej liście – pomiń
                if vanity_name in BLACKLIST:
                    continue
                
                # Jeśli status zmienił się na FREE i NIE BYŁO POWIADOMIENIA
                if status == "FREE" and not was_notified:
                    print(f"🔥🔥🔥 {vanity_name} JEST WOLNE! WYSYŁAM POWIADOMIENIE!")
                    await send_vanity_alert(vanity_name)
                    already_notified[vanity_name] = True  # <--- ZAPAMIĘTUJEMY ŻE WYSŁALIŚMY
                
                # Jeśli status przestał być FREE (zajęte, własny serwer) – resetujemy flagę
                elif status in ["TAKEN", "OWN_SERVER", "BANNED"] and was_notified:
                    print(f"🔄 {vanity_name} zmieniła status na {status} – resetuję flagę powiadomienia")
                    already_notified[vanity_name] = False
                
                # Aktualizuj pamięć statusów
                last_known_status[vanity_name] = {"status": status, "guild_name": data.get("guild_name")}
            
            await asyncio.sleep(30)
                
        except Exception as e:
            print(f"💀 Błąd w pętli: {e}")
            await asyncio.sleep(60)

# ========== URUCHOMIENIE ==========
@bot.event
async def on_ready():
    print(f"✅ Zalogowano jako {bot.user}")
    print(f"📋 Monitorowane vanitki ({len(TARGET_URLS)}):")
    for v in TARGET_URLS:
        print(f"   - {v}")
    print(f"🚫 Czarna lista: {BLACKLIST if BLACKLIST else 'Pusto'}")
    print(f"📢 Kanał: {CHANNEL_ID}")
    print(f"👤 Powiadomienia dla: {YOUR_USER_ID}")
    print("=" * 50)
    bot.loop.create_task(monitor_loop())

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("💀 BRAK BOT_TOKEN!")
    else:
        bot.run(BOT_TOKEN)
