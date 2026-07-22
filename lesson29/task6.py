import math
import multiprocessing


def oblicz_silnie():
    print(f"10! = {math.factorial(10)}")


def main():
    proces = multiprocessing.Process(target=oblicz_silnie)
    proces.start()
    proces.join()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
