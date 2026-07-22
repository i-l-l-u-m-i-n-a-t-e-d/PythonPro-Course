import threading
import time


def praca_watku():
    time.sleep(3)
    print("Wątek zakończył pracę!")


def main():
    watek = threading.Thread(target=praca_watku)
    watek.start()
    print("Główny program czeka na wątek...")
    watek.join()


if __name__ == "__main__":
    main()
