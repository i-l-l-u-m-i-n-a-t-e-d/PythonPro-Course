while True:

    try:
    
        a = float(input("Podaj 1 liczbe: ").replace(",","."))
        b = float(input("Podaj 2 liczbe: ").replace(",","."))

        operation = input("Wybierz operacje (wpisz: +,-,* lub /): ").strip()

        
    
    except ValueError:

        print("Wpisane dane sa niepoprawne.")
    
    else:

        if operation == "+":

            print(f"a+b to: {a+b}")
        
        elif operation == "-":

            print(f"a-b to: {a-b}")

        elif operation == "*":

            print(f"a*b to: {a*b}")

        elif operation == "/":

            try:

                print(f"a/b to: {a/b}")
            
            except ZeroDivisionError:

                print("Nie mozna dzielic przez 0.")
        
        else:

            print("Wprowadzono niepoprawny znak operacji.")
    
    finally:
        
        print("Kolejna operacja...")

