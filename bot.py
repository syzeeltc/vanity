import requests
import os
import time

# ========== ZMIENNE ŚRODOWISKOWE ==========
TOKEN = os.getenv("DISCORD_TOKEN")
if not TOKEN:
    raise ValueError("💀 Ustaw DISCORD_TOKEN w Railway Variables!")

try:
    GUILD_ID = os.getenv("GUILD_ID")
    if not GUILD_ID:
        raise ValueError("💀 Ustaw GUILD_ID w Railway Variables!")
    GUILD_ID = int(GUILD_ID)
except ValueError:
    raise ValueError("💀 GUILD_ID musi być liczbą (samymi cyframi)!")

TARGET_URL = os.getenv("TARGET_URL")
if not TARGET_URL:
    raise ValueError("💀 Ustaw TARGET_URL w Railway Variables!")

# ========== NAGŁÓWKI ==========
headers = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

# ========== FUNKCJA SNIPOWANIA ==========
def snipe():
    url = f"https://discord.com/api/v9/guilds/{GUILD_ID}/vanity-url"
    data = {"code": TARGET_URL}
    
    try:
        r = requests.patch(url, headers=headers, json=data)
        
        # ===== SUKCES =====
        if r.status_code == 200:
            print(f"🔥🔥🔥 PRZECHWYCONE! Vanity: {TARGET_URL} 🔥🔥🔥")
            return True
        
        # ===== BŁĘDY =====
        elif r.status_code == 401:
            print("💀 TOKEN NIEAKTUALNY! Wyciągnij nowy token z konta!")
            print(f"   Odpowiedź: {r.text}")
            return False
            
        elif r.status_code == 403:
            print("❌ Brak uprawnień! Konto MK musi mieć rolę ADMIN na serwerze!")
            print(f"   Odpowiedź: {r.text}")
            return False
            
        elif r.status_code == 429:
            print("⏳ Rate limit! Czekam 60 sekund...")
            time.sleep(60)
            return snipe()
            
        else:
            print(f"⚠️ Błąd {r.status_code}: {r.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"💀 Błąd sieci: {e}")
        return False
    except Exception as e:
        print(f"💀 Nieznany błąd: {e}")
        return False

# ========== FUNKCJA KEEP-ALIVE ==========
def keep_alive():
    """Odświeża sesję i przedłuża życie tokena"""
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
        if r.status_code == 200:
            print("✅ Sesja żyje i ma się dobrze!")
            return True
        elif r.status_code == 401:
            print("💀 TOKEN WYGASŁ! Wyciągnij nowy!")
            return False
        else:
            print(f"⚠️ Keep-alive: {r.status_code}")
            return True
    except Exception as e:
        print(f"💀 Błąd keep-alive: {e}")
        return False

# ========== GŁÓWNA PĘTLA ==========
print("🚀🚀🚀 ZO STARTUJE BEZ MFA DLA ALPHY! 🚀🚀🚀")
print(f"🎯 Cel: {TARGET_URL} na serwerze {GUILD_ID}")
print("=" * 60)

counter = 0
while True:
    counter += 1
    print(f"\n🔄 Próba #{counter} - {time.strftime('%H:%M:%S')}")
    
    keep_alive()
    success = snipe()
    
    if success:
        print("✅ Zrobione! Snajpowanie działa!")
    else:
        print("⏳ Nie udało się, czekam 5 minut...")
    
    time.sleep(300)
