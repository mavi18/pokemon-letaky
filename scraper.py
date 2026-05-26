import requests
from bs4 import BeautifulSoup
import json
import os
import sys

URL = "https://www.kimbino.sk/hladat/?q=pokemon"
STATE_FILE = "state.json"
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def get_current_flyers():
    # Hlavička, aby sme nevyzerali ako bot a Kimbino nás nezablokovalo
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    
    response = requests.get(URL, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    
    current_flyers = {}
    
    # Kimbino zvyčajne obaľuje letáky do odkazov (a tagy). 
    # Hľadáme všetky odkazy, ktoré by mohli reprezentovať leták.
    # Upozornenie: Ak Kimbino mení štruktúru, selektory bude možno potrebné upraviť.
    for a_tag in soup.find_all('a', href=True):
        title = a_tag.get_text(strip=True).lower()
        href = a_tag['href']
        
        # Ak odkaz alebo text obsahuje slovo pokemon a vyzerá to ako leták
        if 'pokemon' in title or 'pokemon' in href.lower():
            # Zabezpečíme absolútnu URL
            full_url = href if href.startswith('http') else f"https://www.kimbino.sk{href}"
            current_flyers[full_url] = title

    return current_flyers

def send_notification(message, url):
    if not NTFY_TOPIC:
        print("Chyba: NTFY_TOPIC nie je nastavený.")
        return
        
    ntfy_url = f"https://ntfy.sh/{NTFY_TOPIC}"
    headers = {
        "Title": "Nový Pokémon leták!",
        "Tags": "tada,shopping_bags",
        "Click": url
    }
    requests.post(ntfy_url, data=message.encode('utf-8'), headers=headers)

def main():
    # Načítanie starého stavu
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                old_urls = set(json.load(f))
            except json.JSONDecodeError:
                old_urls = set()
    else:
        old_urls = set()

    # Získanie aktuálneho stavu
    try:
        current_flyers = get_current_flyers()
        current_urls = set(current_flyers.keys())
    except Exception as e:
        print(f"Chyba pri sťahovaní stránky: {e}")
        sys.exit(1)

    # Porovnanie
    new_urls = current_urls - old_urls
    removed_urls = old_urls - current_urls

    # Notifikovanie o nových letákoch
    if new_urls:
        for url in new_urls:
            msg = f"Našiel sa nový leták obsahujúci Pokémon: {url}"
            print(msg)
            send_notification(msg, url)
    else:
        print("Žiadne nové letáky.")

    if removed_urls:
        print(f"Boli odstránené staré letáky: {removed_urls}")

    # Uloženie aktuálneho stavu (prepíše sa starý stav, odstránené letáky zmiznú)
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(current_urls), f, indent=4)

if __name__ == "__main__":
    main()

