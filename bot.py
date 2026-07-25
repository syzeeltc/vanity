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
        print(f"✅ Bot zalogowany jako {self.user}")
        print(f"🔫 Auto-snajp {len(VANITY_CODES)} kod(ów): {', '.join(VANITY_CODES)}")
        print(f"⏳ Sprawdzam co {CHECK_INTERVAL} min, opóźnienie PATCH {PATCH_DELAY}s")

    async def try_claim(self, code: str):
        """Próbuje zająć vanity przez API serwera."""
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
                err_code = data.get("code")
                err_msg = data.get("message", "")
                return False, f"Error {err_code}: {err_msg}"
            elif resp.status == 403:
                return False, "Brak uprawnień (Manage Server)"
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

            # Krok 1: GET invite — jeśli 200, to na pewno zajęte (pomijamy)
            invite_url = f"https://discord.com/api/v10/invites/{code}"
            async with self.session.get(invite_url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    owner = data.get("guild", {}).get("name", "???")
                    print(f"❌ {code} zajęty przez: {owner}")
                    continue
                elif resp.status == 404:
                    print(f"⚠️ {code} wygląda na wolny (404) — próbuję zająć PATCH-em...")
                else:
                    print(f"❓ {code} GET status: {resp.status}")
                    continue

            # Krok 2: PATCH — próba zajęcia (to odróżnia wolny od zbanowanego)
            success, info = await self.try_claim(code)
            
            if success:
                print(f"🎉🎉🎉 SUKCES! Zajęto {code}!")
                self.claimed.add(code)
                if channel:
                    await channel.send(
                        f"<@{YOUR_ID}> ✅ **SUKCES!** Vanity `discord.gg/{code}` zostało PRZYDZIELONE Twojemu serwerowi!\n"
                        f"🎉 Link działa: https://discord.gg/{code}"
                    )
                if len(self.claimed) == len(VANITY_CODES):
                    print("✅ Wszystkie kody zajęte. Kończę.")
                    self.monitor.stop()
                    return
            else:
                print(f"❌ Nie udało się zająć {code}: {info}")
                if "Rate limit" in str(info):
                    await asyncio.sleep(60)

            # Opóźnienie między PATCH-ami różnych kodów (unika rate limitu)
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
