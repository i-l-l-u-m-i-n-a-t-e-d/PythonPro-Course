import multiprocessing


def potega(liczba, pot):
    print(f"{liczba}^{pot} = {liczba ** pot}")


def main():
    proces = multiprocessing.Process(target=potega, args=(5, 3))
    proces.start()
    proces.join()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
