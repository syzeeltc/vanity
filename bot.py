import discord
from discord.ext import commands, tasks
import aiohttp
import os
from datetime import datetime, timedelta

TOKEN = os.getenv("DISCORD_TOKEN")
VANITY_CODES = [c.strip() for c in os.getenv("VANITY_CODES", "").split(",") if c.strip()]
GUILD_ID = int(os.getenv("GUILD_ID"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) if os.getenv("CHANNEL_ID") else None
YOUR_ID = int(os.getenv("YOUR_ID"))
CHECK_INTERVAL = 1  # co 1 minutę
ALERT_COOLDOWN_MINUTES = 10  # po powiadomieniu czeka 10 min zanim znowu sprawdzi ten kod

class VanityMonitorBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.session = None
        self.notified = {}  # code -> datetime kiedy ostatnio powiadomiono
        self.last_status = {}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.monitor.start()

    async def on_ready(self):
        print(f"Bot zalogowany jako {self.user}")
        print(f"Monitoruje: {', '.join(VANITY_CODES)} co {CHECK_INTERVAL} min")
        guild = self.get_guild(GUILD_ID)
        if guild:
            print(f"Serwer: {guild.name} (boost tier: {guild.premium_tier})")

    async def check_vanity(self, code: str):
        url = f"https://discord.com/api/v10/invites/{code}"
        async with self.session.get(url) as resp:
            if resp.status == 200:
                data = await resp.json()
                owner = data.get("guild", {}).get("name", "???")
                return "taken", owner
            elif resp.status == 404:
                return "free_or_banned", None
            elif resp.status == 429:
                return "ratelimit", None
            else:
                return f"error_{resp.status}", None

    async def send_alert(self, code: str, user: discord.User, channel=None):
        embed = discord.Embed(
            title="Vanity URL Monitor",
            description=f"Kod `discord.gg/{code}` zwrócił **404**.",
            color=0xFFA500,
            timestamp=datetime.utcnow()
        )
        embed.add_field(
            name="Status",
            value="Może być wolny LUB w cooldown/zbanowany przez Discorda.",
            inline=False
        )
        embed.add_field(
            name="Co zrobić?",
            value="Wejdź w Ustawienia serwera → Zaproszenia → Custom Link i sprawdź czy da się ustawić.",
            inline=False
        )
        embed.set_footer(text="Sprawdź natychmiast! Inni też mogą mieć snajpery.")

        dm_sent = False
        try:
            await user.send(embed=embed)
            print(f"Wyslano DM do {user} o {code}")
            dm_sent = True
        except discord.Forbidden:
            print(f"Nie moge wyslac DM do {user}")

        if channel:
            try:
                if dm_sent:
                    await channel.send(f"<@{YOUR_ID}> Wysłano DM o vanity `discord.gg/{code}` — sprawdź wiadomości prywatne!")
                else:
                    await channel.send(f"<@{YOUR_ID}> Vanity `discord.gg/{code}` może być wolny! Sprawdź ASAP!", embed=embed)
            except Exception as e:
                print(f"Blad wysylania na kanal: {e}")

    @tasks.loop(minutes=CHECK_INTERVAL)
    async def monitor(self):
        await self.wait_until_ready()
        guild = self.get_guild(GUILD_ID)
        channel = guild.get_channel(CHANNEL_ID) if guild and CHANNEL_ID else None
        user = await self.fetch_user(YOUR_ID)
        now = datetime.utcnow()

        for code in VANITY_CODES:
            # Sprawdź cooldown
            if code in self.notified:
                time_since = now - self.notified[code]
                if time_since < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    remaining = ALERT_COOLDOWN_MINUTES - time_since.seconds // 60
                    print(f"{code} w cooldownie powiadomienia ({remaining} min zostalo)")
                    continue

            status, info = await self.check_vanity(code)
            self.last_status[code] = (status, info, now)

            if status == "taken":
                print(f"{code} zajety przez: {info}")
            elif status == "free_or_banned":
                print(f"{code} 404 - wysylam powiadomienie")
                await self.send_alert(code, user, channel)
                self.notified[code] = now
            elif status == "ratelimit":
                print(f"Rate limit na {code}")
            else:
                print(f"{code} blad: {status}")

    @monitor.before_loop
    async def before_monitor(self):
        await self.wait_until_ready()

    @commands.command()
    async def check(self, ctx, code: str = None):
        if not code:
            if not VANITY_CODES:
                await ctx.send("Brak skonfigurowanych kodow. Uzyj: `!check kod`")
                return
            code = VANITY_CODES[0]

        status, info = await self.check_vanity(code)
        self.last_status[code] = (status, info, datetime.utcnow())

        if status == "taken":
            await ctx.send(f"❌ `discord.gg/{code}` jest zajęty przez: **{info}**")
        elif status == "free_or_banned":
            await ctx.send(f"⚠️ `discord.gg/{code}` zwraca **404**. Może być wolny lub w cooldown. Sprawdź w ustawieniach serwera!")
        elif status == "ratelimit":
            await ctx.send(f"⏳ Rate limit — spróbuj później.")
        else:
            await ctx.send(f"❓ Nieznany status: {status}")

    @commands.command()
    async def status(self, ctx):
        if not self.last_status:
            await ctx.send("Jeszcze nic nie sprawdzono. Poczekaj na pierwszy cykl lub użyj `!check kod`")
            return

        embed = discord.Embed(title="Status Vanity URL", color=0x3498db)
        for code, (status, info, checked_at) in self.last_status.items():
            if status == "taken":
                val = f"❌ Zajęty przez: {info}"
            elif status == "free_or_banned":
                val = f"⚠️ 404 (wolny/cooldown)"
            else:
                val = f"❓ {status}"
            embed.add_field(name=f"discord.gg/{code}", value=f"{val}\n🕒 {checked_at.strftime('%H:%M:%S')}", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def reset(self, ctx, code: str = None):
        if code:
            self.notified.pop(code, None)
            await ctx.send(f"Resetowano powiadomienie dla `{code}`. Bot będzie ponownie monitorował.")
        else:
            self.notified.clear()
            await ctx.send("Resetowano wszystkie powiadomienia.")

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = VanityMonitorBot()
bot.run(TOKEN)
