import requests
import os
import time

TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("💀 Ustaw DISCORD_TOKEN!")

GUILD_ID = os.getenv("GUILD_ID")
if not GUILD_ID:
    raise ValueError("💀 Ustaw GUILD_ID!")

TARGET_URL = os.getenv("TARGET_URL")
if not TARGET_URL:
    raise ValueError("💀 Ustaw TARGET_URL!")

headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def snipe():
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/vanity-url"
    data = {"code": TARGET_URL}
    
    try:
        r = requests.patch(url, headers=headers, json=data)
        
        if r.status_code == 200:
            print(f"🔥 Przechwycone! Vanity: {TARGET_URL}")
            return True
        elif r.status_code == 401:
            print("💀 TOKEN NIEAKTUALNY! Wyciągnij nowy token z konta!")
            print(f"   Odpowiedź: {r.text}")
        elif r.status_code == 403:
            print("❌ Brak uprawnień! Konto MK musi mieć rolę ADMIN na serwerze!")
            print(f"   Odpowiedź: {r.text}")
        elif r.status_code == 400:
            print(f"⚠️ Błąd 400 – złe dane: {r.text}")
        else:
            print(f"⚠️ Błąd {r.status_code}: {r.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"💀 Błąd sieci: {e}")
    
    return False

print("🚀 Zo startuje z requests (self-bot) dla Alphy!")
print(f"🎯 Cel: {TARGET_URL} na serwerze {GUILD_ID}")

while True:
    snipe()
    print("⏳ Czekam 5 minut...")
    time.sleep(300)
