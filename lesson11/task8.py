while True:

    try:

        a = float(input("Podaj 1 liczbę: ").replace(",", "."))
        b = float(input("Podaj 2 liczbę: ").replace(",", "."))

        operacja = input("Wybierz operację (+, -, *, /): ").strip()

        if operacja == "+":

            wynik = a + b

        elif operacja == "-":

            wynik = a - b

        elif operacja == "*":

            wynik = a * b

        elif operacja == "/":

            wynik = a / b

        else:

            wynik = None
            print("Błąd: niepoprawna operacja.")

    except ValueError:

        print("Błąd: wpisane dane nie są liczbą.")

    except ZeroDivisionError:

        print("Błąd: nie można dzielić przez zero.")

    else:

        if wynik is not None:
            
            print(f"Wynik: {wynik}")

    finally:
        print("Koniec obliczeń.")