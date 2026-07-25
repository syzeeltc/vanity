import discord
from discord.ext import commands, tasks
import aiohttp
import os
import asyncio
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
VANITY_CODES = [c.strip() for c in os.getenv("VANITY_CODES", "").split(",") if c.strip()]
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
YOUR_ID = int(os.getenv("YOUR_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))
PATCH_DELAY = int(os.getenv("PATCH_DELAY", "10"))

class VanitySniperBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.session = None
        self.claimed = set()

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.monitor.start()

    async def on_ready(self):
        print(f"Bot zalogowany jako {self.user}")
        print(f"Monitoruje: {', '.join(VANITY_CODES)}")
        
        # DIAGNOSTYKA SERWERA
        guild = self.get_guild(GUILD_ID)
        if guild:
            print(f"Serwer: {guild.name}")
            print(f"Boost tier: {guild.premium_tier}")
            print(f"Boost count: {guild.premium_subscription_count}")
            print(f"Features: {guild.features}")
            if "VANITY_URL" in guild.features:
                print("✅ Serwer MA feature VANITY_URL")
            else:
                print("❌ Serwer NIE MA feature VANITY_URL - potrzebne 14 boostów (lvl 3)!")
        else:
            print(f"❌ Nie znaleziono serwera o ID {GUILD_ID}")

    async def try_claim(self, code):
        url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/vanity-url"
        headers = {
            "Authorization": f"Bot {TOKEN}",
            "Content-Type": "application/json"
        }
        payload = {"code": code}
        
        async with self.session.patch(url, headers=headers, json=payload) as resp:
            if resp.status == 200:
                data = await resp.json()
                return True, data
            elif resp.status == 400:
                data = await resp.json()
                return False, data.get("message", "Error 400")
            elif resp.status == 403:
                data = await resp.json()
                err_code = data.get("code", "???")
                return False, f"403 Missing Access (code {err_code}) - brak VANITY_URL feature?"
            elif resp.status == 429:
                return False, "Rate limit"
            else:
                return False, f"Status {resp.status}"

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def monitor(self):
        await self.wait_until_ready()
        guild = self.get_guild(GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID) if guild else None

        for code in VANITY_CODES:
            if code in self.claimed:
                continue

            invite_url = f"https://discord.com/api/v10/invites/{code}"
            async with self.session.get(invite_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    owner = data.get("guild", {}).get("name", "???")
                    print(f"{code} zajety przez: {owner}")
                    continue
                elif resp.status == 404:
                    print(f"{code} wolny? Probuje zajac...")
                else:
                    print(f"{code} GET status: {resp.status}")
                    continue

            success, info = await self.try_claim(code)
            
            if success:
                print(f"SUKCES! Zajeto {code}!")
                self.claimed.add(code)
                if channel:
                    await channel.send(
                        f"<@{YOUR_ID}> SUKCES! discord.gg/{code} jest TWOJE!"
                    )
                if len(self.claimed) == len(VANITY_CODES):
                    self.monitor.stop()
                    return
            else:
                print(f"Nie udalo sie zajac {code}: {info}")
                if "Rate limit" in str(info):
                    await asyncio.sleep(60)

            await asyncio.sleep(PATCH_DELAY)

    @monitor.before_loop
    async def before_monitor(self):
        await self.wait_until_ready()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = VanitySniperBot()
bot.run(TOKEN)
