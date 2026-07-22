import argparse
import queue
import threading
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from html.parser import HTMLParser
from urllib.error import URLError
from urllib.parse import urldefrag, urljoin, urlsplit
from urllib.request import Request, urlopen


class ParserLinkow(HTMLParser):
    def __init__(self):
        super().__init__()
        self.linki = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() == "a":
            adres = dict(attrs).get("href")
            if adres:
                self.linki.append(adres)


def pobierz_linki(adres):
    zapytanie = Request(adres, headers={"User-Agent": "Lesson30Crawler/1.0"})
    try:
        with urlopen(zapytanie, timeout=10) as odpowiedz:
            if odpowiedz.headers.get_content_type() != "text/html":
                return []
            tekst = odpowiedz.read().decode(odpowiedz.headers.get_content_charset() or "utf-8", errors="ignore")
    except (URLError, OSError, ValueError) as blad:
        print(f"Błąd pobierania {adres}: {blad}")
        return []

    parser = ParserLinkow()
    parser.feed(tekst)
    print(f"Odwiedzono: {adres}")
    return parser.linki


def link_z_tej_samej_domeny(link, baza, domena):
    adres, _ = urldefrag(urljoin(baza, link))
    czesci = urlsplit(adres)
    if czesci.scheme not in ("http", "https") or czesci.netloc.lower() != domena:
        return None
    return adres


def crawl(adres_startowy, limit, liczba_watkow):
    domena = urlsplit(adres_startowy).netloc.lower()
    if not domena:
        raise ValueError("adres startowy musi zawierać domenę")

    kolejka_stron = queue.Queue()
    kolejka_stron.put(adres_startowy)
    zaplanowane = {adres_startowy}
    odwiedzone = set()
    blokada_zbiorow = threading.Lock()
    przyszle = {}

    with ThreadPoolExecutor(max_workers=liczba_watkow) as pula:
        while przyszle or not kolejka_stron.empty():
            while len(przyszle) < liczba_watkow and not kolejka_stron.empty():
                with blokada_zbiorow:
                    if len(odwiedzone) >= limit:
                        break
                adres = kolejka_stron.get()
                with blokada_zbiorow:
                    odwiedzone.add(adres)
                przyszle[pula.submit(pobierz_linki, adres)] = adres

            if not przyszle:
                break

            zakonczone, _ = wait(przyszle, return_when=FIRST_COMPLETED)
            for przyszlosc in zakonczone:
                adres = przyszle.pop(przyszlosc)
                for link in przyszlosc.result():
                    poprawny_link = link_z_tej_samej_domeny(link, adres, domena)
                    if poprawny_link is None:
                        continue
                    with blokada_zbiorow:
                        if poprawny_link not in zaplanowane and len(zaplanowane) < limit:
                            zaplanowane.add(poprawny_link)
                            kolejka_stron.put(poprawny_link)

    print(f"Łącznie odwiedzono stron: {len(odwiedzone)}")


def main():
    parser = argparse.ArgumentParser(description="Prosty wielowątkowy crawler jednej domeny.")
    parser.add_argument("url", nargs="?", default="https://example.com/", help="adres startowy")
    parser.add_argument("--limit", type=int, default=50, help="maksymalna liczba stron")
    parser.add_argument("--watki", type=int, default=5, help="liczba wątków")
    args = parser.parse_args()

    if args.limit < 1 or args.watki < 1:
        parser.error("limit i liczba wątków muszą być dodatnie")
    crawl(args.url, args.limit, args.watki)


if __name__ == "__main__":
    main()
