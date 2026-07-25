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
CHECK_INTERVAL = 1  # co 1 minutę sprawdza wszystkie
ALERT_COOLDOWN_MINUTES = 30  # po alarmie czeka 30 min zanim znowu alarmuje ten kod

class SmartVanityBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.session = None
        # Historia: code -> {"status": "taken"|"free"|"unknown", "since": datetime, "last_alert": datetime|None}
        self.history = {}
        self.init_history()

    def init_history(self):
        for code in VANITY_CODES:
            self.history[code] = {"status": "unknown", "since": datetime.utcnow(), "last_alert": None}

    async def setup_hook(self):
        self.session = aiohttp.ClientSession()
        self.monitor.start()

    async def on_ready(self):
        print(f"Bot zalogowany jako {self.user}")
        print(f"Smart Monitor aktywny dla: {', '.join(VANITY_CODES)}")
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
                return "free", None
            elif resp.status == 429:
                return "ratelimit", None
            else:
                return f"error_{resp.status}", None

    async def send_alert(self, code: str, prev_owner: str, user: discord.User, channel):
        embed = discord.Embed(
            title="Vanity URL Monitor",
            description=f"Kod `discord.gg/{code}` **WŁAŚNIE SIĘ ZWOLNIŁ**!",
            color=0x00FF00,
            timestamp=datetime.utcnow()
        )
        embed.add_field(name="Poprzedni właściciel", value=prev_owner or "Nieznany", inline=False)
        embed.add_field(
            name="Co zrobić?",
            value="Wejdź w **Ustawienia serwera → Zaproszenia → Custom Link** i ustaw go NATYCHMIAST!",
            inline=False
        )
        embed.set_footer(text="To jest PRAWDZIWE zwolnienie (kod był zajęty, teraz jest wolny). Szybko!")

        dm_sent = False
        try:
            await user.send(embed=embed)
            print(f"Wyslano DM do {user} o {code}")
            dm_sent = True
        except discord.Forbidden:
            print(f"Nie moge wyslac DM do {user}")

        if channel:
            try:
                msg = f"<@{YOUR_ID}> 🚨 **Vanity `discord.gg/{code}` WŁAŚNIE SIĘ ZWOLNIŁ!**"
                if dm_sent:
                    msg += " (DM wysłane)"
                await channel.send(msg, embed=embed)
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
            hist = self.history[code]
            status, info = await self.check_vanity(code)

            # Sprawdź cooldown alarmu
            if hist["last_alert"]:
                time_since_alert = now - hist["last_alert"]
                if time_since_alert < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    # W cooldownzie — aktualizuj status ale nie alarmuj
                    hist["status"] = status
                    hist["since"] = now
                    print(f"{code}: {status} (w cooldownie alarmu)")
                    continue

            if status == "taken":
                # Kod zajęty — aktualizuj historię
                if hist["status"] != "taken":
                    print(f"{code}: teraz zajety przez {info}")
                else:
                    print(f"{code}: nadal zajety przez {info}")
                hist["status"] = "taken"
                hist["since"] = now
                hist["owner"] = info

            elif status == "free":
                # Kod zwraca 404
                if hist["status"] == "taken":
                    # BYŁ ZAJĘTY, TERAZ WOLNY -> ALARM!
                    prev_owner = hist.get("owner", "Nieznany")
                    print(f"🚨 {code}: ZWOLNIONY! (był: {prev_owner})")
                    await self.send_alert(code, prev_owner, user, channel)
                    hist["last_alert"] = now
                    hist["status"] = "free"
                    hist["since"] = now
                elif hist["status"] == "unknown":
                    # Pierwszy check i od razu 404 — może być zbanowany, nie alarmujemy
                    print(f"{code}: 404 od startu (zbanowany/cooldown?) — ciche monitorowanie")
                    hist["status"] = "free"
                    hist["since"] = now
                else:
                    # Nadal 404 — ciche logowanie
                    print(f"{code}: nadal 404 (zbanowany/cooldown)")
                    hist["since"] = now

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
        hist = self.history.get(code, {})

        if status == "taken":
            await ctx.send(f"❌ `discord.gg/{code}` jest zajęty przez: **{info}**")
        elif status == "free":
            if hist.get("status") == "taken":
                await ctx.send(f"🚨 `discord.gg/{code}` **WŁAŚNIE SIĘ ZWOLNIŁ**! Sprawdź w ustawieniach serwera!")
            else:
                await ctx.send(f"⚠️ `discord.gg/{code}` zwraca 404. Może być wolny LUB zbanowany/cooldown.")
        elif status == "ratelimit":
            await ctx.send(f"⏳ Rate limit — spróbuj później.")
        else:
            await ctx.send(f"❓ Nieznany status: {status}")

    @commands.command()
    async def status(self, ctx):
        embed = discord.Embed(title="Smart Vanity Monitor", color=0x3498db)
        for code, hist in self.history.items():
            status = hist["status"]
            since = hist["since"].strftime("%H:%M:%S")
            if status == "taken":
                owner = hist.get("owner", "???")
                val = f"❌ Zajęty przez: {owner}\n🕒 od {since}"
            elif status == "free":
                if hist.get("last_alert"):
                    val = f"⚠️ 404 — alarm wysłano {hist['last_alert'].strftime('%H:%M:%S')}"
                else:
                    val = f"🔇 404 od startu (zbanowany/cooldown?)\n🕒 od {since}"
            else:
                val = f"❓ Nieznany\n🕒 od {since}"
            embed.add_field(name=f"discord.gg/{code}", value=val, inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def reset(self, ctx, code: str = None):
        if code:
            if code in self.history:
                self.history[code]["last_alert"] = None
                await ctx.send(f"Resetowano alarm dla `{code}`.")
            else:
                await ctx.send(f"Nie znam kodu `{code}`.")
        else:
            for c in self.history:
                self.history[c]["last_alert"] = None
            await ctx.send("Resetowano wszystkie alarmy.")

    async def close(self):
        if self.session:
            await self.session.close()
        await super().close()

bot = SmartVanityBot()
bot.run(TOKEN)
