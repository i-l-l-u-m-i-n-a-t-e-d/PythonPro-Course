import threading


def przedstaw_sie(numer):
    print(f"Jestem wątkiem numer {numer}")


def main():
    watki = []
    for numer in range(1, 6):
        watek = threading.Thread(target=przedstaw_sie, args=(numer,))
        watki.append(watek)
        watek.start()

    for watek in watki:
        watek.join()


if __name__ == "__main__":
    main()
