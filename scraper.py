import requests
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import json
import os
import sys

URL = "https://www.kimbino.sk/hladat/?q=pokemon"
STATE_FILE = "state.json"
NTFY_TOPIC = os.getenv("NTFY_TOPIC")

def get_current_flyers():
    current_flyers = {}
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        print("Načítavam stránku...")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        
        print("Čakám 5 sekúnd na zobrazenie letákov...")
        page.wait_for_timeout(5000)
        
        html = page.content()
        browser.close()

    # Parsovanie HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Hľadáme všetky odkazy
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        # NAJPRÍSNEJŠÍ FILTER: 
        # Berieme len to, čo má v adrese "-letak-" a zároveň odkazuje na konkrétnu stranu "#page_"
        if '-letak-' in href and '#page_' in href:
            full_url = f"https://www.kimbino.sk{href}" if href.startswith('/') else href
            current_flyers[full_url] = full_url

    return current_flyers

def send_notification(message, url):
    if not NTFY_TOPIC:
        print("Chyba: NTFY_TOPIC nie je nastavený.")
        return
        
    ntfy_url = "https://ntfy.sh/"
    
    # Posielame dáta ako JSON, ktorý natívne podporuje diakritiku (UTF-8)
    payload = {
        "topic": NTFY_TOPIC,
        "title": "Nový Pokémon leták!",
        "message": message,
        "tags": ["tada", "shopping_bags"],
        "click": url
    }
    
    requests.post(ntfy_url, json=payload)

def main():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            try:
                old_urls = set(json.load(f))
            except json.JSONDecodeError:
                old_urls = set()
    else:
        old_urls = set()

    try:
        current_flyers = get_current_flyers()
        current_urls = set(current_flyers.keys())
        print(f"Nájdených REÁLNYCH letákov celkovo: {len(current_urls)}")
    except Exception as e:
        print(f"Chyba pri sťahovaní stránky: {e}")
        sys.exit(1)

    new_urls = current_urls - old_urls
    removed_urls = old_urls - current_urls

    if new_urls:
        for url in new_urls:
            msg = f"Našiel sa nový leták: {url}"
            print(msg)
            send_notification(msg, url)
    else:
        print("Žiadne nové letáky (všetko už bolo videné).")

    if removed_urls:
        print(f"Boli odstránené staré/neplatné letáky: {len(removed_urls)} ks")

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(current_urls), f, indent=4)

if __name__ == "__main__":
    main()
