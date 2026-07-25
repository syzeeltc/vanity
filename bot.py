import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
VANITY_CODE = os.getenv("VANITY_CODE")        # np. "moj-serwer"
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
YOUR_ID = int(os.getenv("YOUR_ID"))
CHECK_EVERY_MINUTES = int(os.getenv("CHECK_INTERVAL", "30"))

class VanityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.session = None

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.monitor.start()

    async def on_ready(self):
        print(f"✅ Bot zalogowany jako {self.user}")
        print(f"🔍 Monitoruję: discord.gg/{VANITY_CODE}")

    @tasks.loop(minutes=CHECK_EVERY_MINUTES)
    async def monitor(self):
        await self.wait_until_ready()
        url = f"https://discord.com/api/v10/invites/{VANITY_CODE}"
        
        async with self.session.get(url) as resp:
            if resp.status == 404:
                guild = self.get_guild(GUILD_ID)
                channel = guild.get_channel(CHANNEL_ID) if guild else None
                if channel:
                    await channel.send(
                        f"<@{YOUR_ID}> 🚨 **Vanity `discord.gg/{VANITY_CODE}` jest WOLNY!**\n"
                        f"⚡ Wejdź w **Ustawienia serwera → Zaproszenia → Custom Link** i ustaw go!\n"
                        f"🕒 {datetime.now().strftime('%H:%M:%S')}"
                    )
                self.monitor.stop()
            elif resp.status == 200:
                data = await resp.json()
                name = data.get("guild", {}).get("name", "???")
                print(f"❌ Zajęty przez: {name}")
            elif resp.status == 429:
                print("⚠️ Rate limit")

    @monitor.before_loop
    async def before_monitor(self):
        await self.wait_until_ready()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = VanityBot()
bot.run(TOKEN)
