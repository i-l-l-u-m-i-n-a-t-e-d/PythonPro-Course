import random
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


def analizuj_sentyment(zdanie):
    time.sleep(random.uniform(0.5, 2.0))
    return random.choice(["Pozytywny", "Negatywny", "Neutralny"])


def main():
    opinie = [
        "Produkt jest bardzo wygodny.", "Bateria rozładowała się za szybko.",
        "Dostawa dotarła przed czasem.", "Instrukcja jest niejasna.",
        "Kolor wygląda świetnie.", "Cena jest zdecydowanie zbyt wysoka.",
        "Obsługa klienta pomogła mi od razu.", "Urządzenie przestało działać po tygodniu.",
        "Montaż był prosty.", "Opakowanie przyszło uszkodzone.",
        "Jakość wykonania pozytywnie mnie zaskoczyła.", "Brakuje ważnej funkcji.",
        "Rozmiar idealnie pasuje.", "Aplikacja często się zawiesza.",
        "Polecam ten produkt znajomym.", "Zdjęcia w ofercie były mylące.",
        "Materiały są przyjemne w dotyku.", "Zwrot pieniędzy trwał za długo.",
        "Produkt spełnia moje oczekiwania.", "Nie kupię go ponownie.",
    ]

    start = time.perf_counter()
    wyniki = [None] * len(opinie)
    with ThreadPoolExecutor(max_workers=5) as pula:
        przyszle = {pula.submit(analizuj_sentyment, opinia): indeks for indeks, opinia in enumerate(opinie)}
        for przyszlosc in as_completed(przyszle):
            wyniki[przyszle[przyszlosc]] = przyszlosc.result()
    czas = time.perf_counter() - start

    for opinia, sentyment in zip(opinie, wyniki):
        print(f"{sentyment}: {opinia}")
    print(f"Czas analizy 20 opinii: {czas:.2f} s")


if __name__ == "__main__":
    main()
