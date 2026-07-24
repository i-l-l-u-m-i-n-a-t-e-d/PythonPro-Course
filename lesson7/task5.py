file = open("log.txt", "a")

try:

    while True:

        try:

            a = float(input("Podaj 1 liczbe: ").replace(",", "."))
            b = float(input("Podaj 2 liczbe: ").replace(",", "."))

            operation = input(
                "Wybierz operacje (wpisz: +,-,* lub /): "
            ).strip()

            if operation == "+":

                print(f"a+b to: {a+b}")

            elif operation == "-":

                print(f"a-b to: {a-b}")

            elif operation == "*":

                print(f"a*b to: {a*b}")

            elif operation == "/":

                print(f"a/b to: {a/b}")

            else:

                raise ValueError("Wprowadzono niepoprawny znak operacji.")

        except Exception as e:

            error = f"{type(e).__name__}: {str(e)}\n"
            print(error, end="")
            file.write(error)

        print("Kolejna operacja...")

finally:

    file.close()
