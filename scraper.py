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
        
        # ZMENA TU: Použijeme domcontentloaded namiesto networkidle a pridáme timeout 60s
        # Zamedzíme tak padaniu kvôli reklamám a trackerom, ktoré sa sťahujú na pozadí.
        print("Načítavam stránku...")
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        
        # Natvrdo počkáme 5 sekúnd, kým Kimbino vyrenderuje výsledky cez JavaScript
        print("Čakám 5 sekúnd na zobrazenie letákov...")
        page.wait_for_timeout(5000)
        
        html = page.content()
        browser.close()

    # Parsovanie HTML
    soup = BeautifulSoup(html, 'html.parser')
    
    # Hľadáme všetky odkazy
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        
        # Heuristika: Letáky majú zvyčajne url v tvare "/obchod/nazov-letaku/"
        # Ignorujeme základné odkazy ako /kontakt, /prihlasenie, a berieme len tie, ktoré vyzerajú ako leták (obsahujú pomlčku)
        if href.startswith('/') and '-' in href and len(href) > 10:
            full_url = f"https://www.kimbino.sk{href}"
            current_flyers[full_url] = full_url

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
        print(f"Nájdených odkazov celkovo: {len(current_urls)}")
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
        print(f"Boli odstránené staré letáky: {removed_urls}")

    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(list(current_urls), f, indent=4)

if __name__ == "__main__":
    main()
