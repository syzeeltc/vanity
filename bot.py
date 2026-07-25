import requests
import os
import time
import discord
from discord import app_commands
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
    "wymiensiano",
    "supervanitka",
    "megafajna"
]

# ========== PAMIĘĆ STATUSÓW ==========
# Przechowuje poprzedni status każdej vanity
last_known_status = {}

# ========== KONFIGURACJA BOTA ==========
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
tree = bot.tree

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
            
            # Sprawdź czy to nasz serwer
            if guild_id and int(guild_id) == GUILD_ID:
                return "OWN_SERVER", guild_name
            else:
                return "TAKEN", guild_name
        
        # ===== 404 =====
        elif r.status_code == 404:
            try:
                error_data = r.json()
                error_msg = error_data.get("message", "").lower()
                
                # Komunikaty o banie
                banned_keywords = ["invalid", "banned", "suspended", "restricted", "vanity", "not found"]
                
                if any(keyword in error_msg for keyword in banned_keywords):
                    # Sprawdź czy wcześniej była zajęta
                    previous = last_known_status.get(vanity_name)
                    
                    # Jeśli wcześniej była zajęta (np. przez nasz serwer) i teraz jest 404 -> jest WOLNA
                    if previous and previous.get("status") in ["TAKEN", "OWN_SERVER"]:
                        print(f"🔥 {vanity_name} ZOSTAŁA ZWOLNIONA!")
                        return "FREE", None
                    else:
                        return "BANNED", None
                else:
                    return "FREE", None
            except:
                return "FREE", None
        
        # ===== 429 =====
        elif r.status_code == 429:
            print(f"⏳ Rate limit dla {vanity_name}, czekam 60s...")
            time.sleep(60)
            return check_single_vanity(vanity_name)
        
        # ===== 403 =====
        elif r.status_code == 403:
            return "BANNED", None
        
        # ===== INNE =====
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
        
        # Zapamiętaj status
        last_known_status[vanity] = {"status": status, "guild_name": guild_name}
        
        print(f"📊 {vanity}: {status}" + (f" ({guild_name})" if guild_name else ""))
    return results

# ========== POWIADOMIENIA ==========
async def send_vanity_alert(vanity_name, status, guild_name=None):
    if status == "FREE":
        title = "🚨🚨🚨 WOLNE!"
        emoji = "🔥"
        message = f"🎯 **Vanity:** `{vanity_name}`\n🔗 **Link:** https://discord.gg/{vanity_name}\n⚡ **USTAW TO TERAZ!**"
    elif status == "BANNED":
        title = "🚫 ZBANOWANE!"
        emoji = "⛔"
        message = f"🎯 **Vanity:** `{vanity_name}`\n⏳ **Zbanowane – czekaj na odbanowanie!**"
    elif status == "OWN_SERVER":
        title = "🏠 TWOJE!"
        emoji = "✅"
        message = f"🎯 **Vanity:** `{vanity_name}`\n✅ **Już należy do twojego serwera!**"
    else:
        return
    
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

# ========== SLASH COMMANDS ==========

@tree.command(name="vanity", description="Sprawdza status wszystkich monitorowanych vanitek")
async def vanity(interaction: discord.Interaction):
    await interaction.response.defer()
    
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
    
    await interaction.followup.send(message)

@tree.command(name="check", description="Sprawdza status konkretnej vanity")
@app_commands.describe(vanity_name="Nazwa vanity do sprawdzenia")
async def check(interaction: discord.Interaction, vanity_name: str):
    await interaction.response.defer()
    
    status, guild_name = check_single_vanity(vanity_name)
    
    if status == "FREE":
        await interaction.followup.send(f"🔥 `{vanity_name}` JEST WOLNE!")
    elif status == "BANNED":
        await interaction.followup.send(f"🚫 `{vanity_name}` JEST ZBANOWANE!")
    elif status == "TAKEN":
        await interaction.followup.send(f"⏳ `{vanity_name}` jest ZAJĘTE przez: {guild_name}")
    elif status == "OWN_SERVER":
        await interaction.followup.send(f"✅ `{vanity_name}` należy do TWOJEGO serwera!")
    else:
        await interaction.followup.send(f"⚠️ Nieznany status: {status}")

@tree.command(name="add", description="Dodaje vanity do monitorowania (tylko Alpha)")
@app_commands.describe(vanity_name="Nazwa vanity do dodania")
async def add(interaction: discord.Interaction, vanity_name: str):
    if interaction.user.id != YOUR_USER_ID:
        await interaction.response.send_message("❌ Tylko Alpha może to robić!", ephemeral=True)
        return
    
    if vanity_name in TARGET_URLS:
        await interaction.response.send_message(f"⚠️ `{vanity_name}` już jest na liście!", ephemeral=True)
    else:
        TARGET_URLS.append(vanity_name)
        await interaction.response.send_message(f"✅ Dodano `{vanity_name}` do monitorowania!")

@tree.command(name="remove", description="Usuwa vanity z monitorowania (tylko Alpha)")
@app_commands.describe(vanity_name="Nazwa vanity do usunięcia")
async def remove(interaction: discord.Interaction, vanity_name: str):
    if interaction.user.id != YOUR_USER_ID:
        await interaction.response.send_message("❌ Tylko Alpha może to robić!", ephemeral=True)
        return
    
    if vanity_name not in TARGET_URLS:
        await interaction.response.send_message(f"⚠️ `{vanity_name}` nie ma na liście!", ephemeral=True)
    else:
        TARGET_URLS.remove(vanity_name)
        await interaction.response.send_message(f"✅ Usunięto `{vanity_name}` z monitorowania!")

@tree.command(name="list", description="Pokazuje wszystkie monitorowane vanitki")
async def list_vanity(interaction: discord.Interaction):
    if interaction.user.id != YOUR_USER_ID:
        await interaction.response.send_message("❌ Tylko Alpha może to robić!", ephemeral=True)
        return
    
    if not TARGET_URLS:
        await interaction.response.send_message("📋 Lista jest pusta!")
        return
    
    message = "📋 **MONITOROWANE VANITKI:**\n"
    for i, vanity_name in enumerate(TARGET_URLS, 1):
        message += f"{i}. `{vanity_name}`\n"
    
    await interaction.response.send_message(message)

@tree.command(name="ping", description="Sprawdza czy bot żyje")
async def ping(interaction: discord.Interaction):
    await interaction.response.send_message(f"🏓 Pong! `{round(bot.latency * 1000)}ms`")

# ========== GŁÓWNA PĘTLA MONITOROWANIA ==========
async def monitor_loop():
    await bot.wait_until_ready()
    print("🔍 Rozpoczynam monitorowanie WIELU VANITEK...")
    print(f"🎯 Liczba vanitek: {len(TARGET_URLS)}")
    print("=" * 50)
    
    while not bot.is_closed():
        try:
            print(f"\n📊 Sprawdzanie {len(TARGET_URLS)} vanitek...")
            results = check_all_vanities()
            
            for vanity_name, data in results.items():
                status = data["status"]
                
                # Jeśli jest WOLNA lub ZBANOWANA – powiadom
                if status in ["FREE", "BANNED"]:
                    await send_vanity_alert(vanity_name, status)
            
            await asyncio.sleep(30)  # Sprawdzaj co 30 sekund (szybciej)
                
        except Exception as e:
            print(f"💀 Błąd w pętli: {e}")
            await asyncio.sleep(60)

# ========== SYNC SLASH COMMANDS ==========
@bot.event
async def on_ready():
    await tree.sync()
    print(f"✅ Zalogowano jako {bot.user}")
    print(f"📋 Monitorowane vanitki ({len(TARGET_URLS)}):")
    for v in TARGET_URLS:
        print(f"   - {v}")
    print(f"📢 Kanał: {CHANNEL_ID}")
    print(f"👤 Powiadomienia dla: {YOUR_USER_ID}")
    print("=" * 50)
    bot.loop.create_task(monitor_loop())

# ========== URUCHOMIENIE ==========
if __name__ == "__main__":
    if not BOT_TOKEN:
        print("💀 BRAK BOT_TOKEN!")
    else:
        bot.run(BOT_TOKEN)
