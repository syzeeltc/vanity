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
    "wymiensiano"
]

# ========== PAMIĘĆ STATUSÓW ==========
last_known_status = {}

# ========== KONFIGURACJA BOTA ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ========== SPRAWDZANIE JEDNEJ VANITY ==========
def check_single_vanity(vanity_name):
    url = f"https://discord.com/api/v9/invites/{vanity_name}"
    
    try:
        r = requests.get(url)
        
        # ===== 200 =====
        if r.status_code == 200:
            data = r.json()
            guild_name = data.get("guild", {}).get("name", "Nieznany serwer")
            guild_id = data.get("guild", {}).get("id")
            
            if guild_id and int(guild_id) == GUILD_ID:
                return "OWN_SERVER", guild_name
            else:
                return "TAKEN", guild_name
        
        # ===== 404 =====
        elif r.status_code == 404:
            try:
                error_data = r.json()
                error_msg = error_data.get("message", "").lower()
                
                # Sprawdź czy to ban
                if "invalid" in error_msg or "banned" in error_msg or "suspended" in error_msg:
                    return "BANNED", None
                else:
                    # Sprawdź czy wcześniej była zajęta
                    previous = last_known_status.get(vanity_name)
                    if previous and previous.get("status") in ["TAKEN", "OWN_SERVER"]:
                        return "FREE", None
                    else:
                        return "UNKNOWN", None
            except:
                return "UNKNOWN", None
        
        # ===== 429 =====
        elif r.status_code == 429:
            print(f"⏳ Rate limit dla {vanity_name}, czekam 60s...")
            time.sleep(60)
            return check_single_vanity(vanity_name)
        
        # ===== 403 =====
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
        last_known_status[vanity] = {"status": status, "guild_name": guild_name}
        print(f"📊 {vanity}: {status}" + (f" ({guild_name})" if guild_name else ""))
    return results

# ========== POWIADOMIENIA ==========
async def send_vanity_alert(vanity_name, status):
    """Wysyła powiadomienie TYLKO gdy vanity jest WOLNE"""
    
    # ⚠️ WYSYŁAJ TYLKO DLA STATUSU "FREE"!
    if status != "FREE":
        print(f"⏳ Pomijam {vanity_name} ({status}) – nie jest wolne")
        return
    
    title = "🚨🚨🚨 WOLNE!"
    emoji = "🔥"
    message = f"🎯 **Vanity:** `{vanity_name}`\n🔗 **Link:** https://discord.gg/{vanity_name}\n⚡ **USTAW TO TERAZ!**"
    
    # DM
    try:
        user = await bot.fetch_user(YOUR_USER_ID)
        if user:
            dm_channel = await user.create_dm()
            await dm_channel.send(f"{emoji}{emoji}{emoji} **{title}** {emoji}{emoji}{emoji}\n{message}")
            print(f"✅ DM dla {vanity_name} wysłane!")
    except Exception as e:
        print(f"💀 Błąd DM ({vanity_name}): {e}")
    
    # Kanał
    try:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"{emoji}{emoji}{emoji} @everyone **{title}** {emoji}{emoji}{emoji}\n{message}\n<@{YOUR_USER_ID}>")
            print(f"✅ Wiadomość na kanale ({vanity_name}) wysłana!")
    except Exception as e:
        print(f"💀 Błąd kanału ({vanity_name}): {e}")

# ========== KOMENDY Z `!` ==========

@bot.command(name="vanity")
async def vanity_cmd(ctx):
    """Sprawdza wszystkie monitorowane vanitki"""
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
        else:
            emoji = "⚠️"
        message += f"{emoji} `{vanity_name}`: {status}\n"
    
    await ctx.send(message)

@bot.command(name="check")
async def check_cmd(ctx, vanity_name: str):
    """Sprawdza konkretną vanity"""
    status, guild_name = check_single_vanity(vanity_name)
    
    if status == "FREE":
        await ctx.send(f"🔥 `{vanity_name}` JEST WOLNE!")
    elif status == "BANNED":
        await ctx.send(f"🚫 `{vanity_name}` JEST ZBANOWANE!")
    elif status == "TAKEN":
        await ctx.send(f"⏳ `{vanity_name}` jest ZAJĘTE przez: {guild_name}")
    elif status == "OWN_SERVER":
        await ctx.send(f"✅ `{vanity_name}` należy do TWOJEGO serwera!")
    else:
        await ctx.send(f"⚠️ Nieznany status: {status}")

@bot.command(name="add")
async def add_cmd(ctx, vanity_name: str):
    """Dodaje vanity do listy"""
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if vanity_name in TARGET_URLS:
        await ctx.send(f"⚠️ `{vanity_name}` już jest na liście!")
    else:
        TARGET_URLS.append(vanity_name)
        await ctx.send(f"✅ Dodano `{vanity_name}` do monitorowania!")

@bot.command(name="remove")
async def remove_cmd(ctx, vanity_name: str):
    """Usuwa vanity z listy"""
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if vanity_name not in TARGET_URLS:
        await ctx.send(f"⚠️ `{vanity_name}` nie ma na liście!")
    else:
        TARGET_URLS.remove(vanity_name)
        await ctx.send(f"✅ Usunięto `{vanity_name}` z monitorowania!")

@bot.command(name="list")
async def list_cmd(ctx):
    """Pokazuje listę monitorowanych vanitek"""
    if ctx.author.id != YOUR_USER_ID:
        await ctx.send("❌ Tylko Alpha może to robić!")
        return
    
    if not TARGET_URLS:
        await ctx.send("📋 Lista jest pusta!")
        return
    
    message = "📋 **MONITOROWANE VANITKI:**\n"
    for i, vanity_name in enumerate(TARGET_URLS, 1):
        message += f"{i}. `{vanity_name}`\n"
    
    await ctx.send(message)

@bot.command(name="ping")
async def ping_cmd(ctx):
    """Sprawdza czy bot żyje"""
    await ctx.send(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

# ========== GŁÓWNA PĘTLA MONITOROWANIA ==========
async def monitor_loop():
    await bot.wait_until_ready()
    print("🔍 Rozpoczynam monitorowanie WIELU VANITEK...")
    print(f"🎯 Liczba vanitek: {len(TARGET_URLS)}")
    print("=" * 50)
    
    # Inicjalizacja statusów
    check_all_vanities()
    
    while not bot.is_closed():
        try:
            print(f"\n📊 Sprawdzanie {len(TARGET_URLS)} vanitek...")
            results = check_all_vanities()
            
            for vanity_name, data in results.items():
                status = data["status"]
                previous = last_known_status.get(vanity_name, {}).get("status")
                
                # ⚠️ PINGUJ TYLKO GDY STATUS ZMIENIŁ SIĘ NA "FREE"
                if status == "FREE" and previous != "FREE":
                    print(f"🔥 {vanity_name} ZMIENIŁA STATUS NA WOLNE!")
                    await send_vanity_alert(vanity_name, status)
                
                # Aktualizuj pamięć
                last_known_status[vanity_name] = {"status": status, "guild_name": data.get("guild_name")}
            
            await asyncio.sleep(30)  # Co 30 sekund
                
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
    print(f"📢 Kanał: {CHANNEL_ID}")
    print(f"👤 Powiadomienia dla: {YOUR_USER_ID}")
    print("=" * 50)
    bot.loop.create_task(monitor_loop())

if __name__ == "__main__":
    if not BOT_TOKEN:
        print("💀 BRAK BOT_TOKEN!")
    else:
        bot.run(BOT_TOKEN)
