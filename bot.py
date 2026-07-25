import requests
import os
import time
import json

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

MFA_CODE = os.getenv("MFA_CODE", "000000")  # Pobieramy z Railway Variables

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
        
        # ===== MFA WYMAGANE =====
        elif r.status_code == 400 and "mfa" in r.text:
            print("💀 Wymagane MFA! Próbuję użyć kodu ze środowiska...")
            
            if MFA_CODE == "000000":
                print("❌ BRAK KODU MFA! Ustaw zmienną MFA_CODE w Railway!")
                print("   (weź aktualny 6-cyfrowy kod z Google Authenticator)")
                return False
            
            try:
                resp = r.json()
                ticket = resp.get("mfa", {}).get("ticket")
                
                if not ticket:
                    print("❌ Brak ticketu MFA w odpowiedzi")
                    return False
                
                # Wysyłamy kod MFA
                mfa_url = "https://discord.com/api/v9/mfa/finish"
                mfa_data = {
                    "code": MFA_CODE,
                    "ticket": ticket
                }
                
                mfa_r = requests.post(mfa_url, headers=headers, json=mfa_data)
                
                if mfa_r.status_code == 200:
                    mfa_resp = mfa_r.json()
                    new_token = mfa_resp.get("token")
                    
                    if new_token:
                        print(f"✅ Nowy token wyciągnięty! {new_token[:20]}...")
                        # Aktualizujemy token w headers i zmiennej
                        global TOKEN, headers
                        TOKEN = new_token
                        headers["Authorization"] = new_token
                        print("🔄 Próbuję jeszcze raz z nowym tokenem...")
                        return snipe()  # Rekurencyjna próba
                    else:
                        print("❌ Nie otrzymano nowego tokena po MFA")
                        print(f"   Odpowiedź: {mfa_r.text}")
                        return False
                        
                elif mfa_r.status_code == 400:
                    print("❌ ZŁY KOD MFA! Zaktualizuj zmienną MFA_CODE na Railway!")
                    print("   (kod z autentykatora zmienia się co 30s, weź aktualny!)")
                    print(f"   Odpowiedź: {mfa_r.text}")
                    return False
                else:
                    print(f"⚠️ Błąd MFA: {mfa_r.status_code}")
                    print(f"   Odpowiedź: {mfa_r.text}")
                    return False
                    
            except json.JSONDecodeError:
                print("💀 Błąd parsowania JSON w odpowiedzi MFA")
                return False
            except Exception as e:
                print(f"💀 Wyjątek w MFA: {e}")
                return False
        
        # ===== INNE BŁĘDY =====
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
            return snipe()  # Próbuj ponownie
            
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
            print("💀 TOKEN WYGASŁ! Potrzebny nowy!")
            return False
        else:
            print(f"⚠️ Keep-alive: {r.status_code}")
            return True
    except Exception as e:
        print(f"💀 Błąd keep-alive: {e}")
        return False

# ========== GŁÓWNA PĘTLA ==========
print("🚀🚀🚀 ZO STARTUJE Z OBSŁUGĄ MFA DLA ALPHY! 🚀🚀🚀")
print(f"🎯 Cel: {TARGET_URL} na serwerze {GUILD_ID}")
print(f"📱 Kod MFA: {MFA_CODE if MFA_CODE != '000000' else '⚠️ NIEUSTAWIONY!'}")
print("=" * 60)

if MFA_CODE == "000000":
    print("⚠️⚠️⚠️ UWAGA: NIE USTAWIŁEŚ KODU MFA! ⚠️⚠️⚠️")
    print("Dodaj zmienną MFA_CODE w Railway Variables z aktualnym kodem z Google Authenticator!")
    print("=" * 60)

counter = 0
while True:
    counter += 1
    print(f"\n🔄 Próba #{counter} - {time.strftime('%H:%M:%S')}")
    
    # Najpierw odśwież sesję
    keep_alive()
    
    # Snipowanie
    success = snipe()
    
    if success:
        print("✅ Zrobione! Snajpowanie działa!")
    else:
        print("⏳ Nie udało się, czekam 5 minut...")
    
    time.sleep(300)  # 5 minut
