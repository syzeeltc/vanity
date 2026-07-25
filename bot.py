import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime

TOKEN = os.getenv("DISCORD_TOKEN")
# Wpisz kody rozdzielone przecinkami, np.: "moj-serwer,inny-kod,trzeci"
VANITY_CODES = [c.strip() for c in os.getenv("VANITY_CODES", "").split(",") if c.strip()]
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID"))
YOUR_ID = int(os.getenv("YOUR_ID"))
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "5"))

class VanityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        super().__init__(command_prefix="!", intents=intents)
        self.session = None
        self.notified = set()  # żeby nie spamować o tym samym kodzie

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.monitor.start()

    async def on_ready(self):
        print(f"✅ Bot zalogowany jako {self.user}")
        print(f"🔍 Monitoruję {len(VANITY_CODES)} kod(y): {', '.join(VANITY_CODES)}")

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def monitor(self):
        await self.wait_until_ready()

        for code in VANITY_CODES:
            if code in self.notified:
                continue

            url = f"https://discord.com/api/v10/invites/{code}"
            async with self.session.get(url) as resp:
                if resp.status == 404:
                    guild = self.get_guild(GUILD_ID)
                    channel = guild.get_channel(CHANNEL_ID) if guild else None
                    if channel:
                        await channel.send(
                            f"<@{YOUR_ID}> 🚨 **Vanity `discord.gg/{code}` jest WOLNY!**\n"
                            f"⚡ Szybko — ustaw w **Ustawienia serwera → Zaproszenia → Custom Link**!\n"
                            f"🕒 {datetime.now().strftime('%H:%M:%S')}"
                        )
                    self.notified.add(code)
                    print(f"🎉 Znaleziono wolny: {code}")

                elif resp.status == 200:
                    data = await resp.json()
                    name = data.get("guild", {}).get("name", "???")
                    print(f"❌ {code} zajęty przez: {name}")

                elif resp.status == 429:
                    print(f"⚠️ Rate limit na {code}")

        # Jeśli wszystkie kody są wolne (lub powiadomione), można zatrzymać
        if len(self.notified) == len(VANITY_CODES):
            print("✅ Wszystkie kody sprawdzone/znalezione. Zatrzymuję monitorowanie.")
            self.monitor.stop()

    @monitor.before_loop
    async def before_monitor(self):
        await self.wait_until_ready()

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = VanityBot()
bot.run(TOKEN)
