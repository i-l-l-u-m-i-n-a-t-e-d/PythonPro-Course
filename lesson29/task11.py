import queue
import random
import threading
import time


def producent(kolejka, koniec):
    while not koniec.wait(1):
        element = random.randint(1, 100)
        kolejka.put(element)
        print(f"Producent dodał: {element}")


def konsument(kolejka, koniec):
    while not koniec.is_set():
        try:
            element = kolejka.get(timeout=0.2)
        except queue.Empty:
            continue

        print(f"Konsument pobrał: {element}")
        koniec.wait(1.5)


def main():
    kolejka = queue.Queue()
    koniec = threading.Event()
    watek_producenta = threading.Thread(target=producent, args=(kolejka, koniec))
    watek_konsumenta = threading.Thread(target=konsument, args=(kolejka, koniec))

    watek_producenta.start()
    watek_konsumenta.start()
    time.sleep(10)
    koniec.set()

    watek_producenta.join()
    watek_konsumenta.join()
    print("Symulacja zakończona po 10 sekundach.")


if __name__ == "__main__":
    main()
