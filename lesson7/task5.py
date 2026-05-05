while True:

    file = open("log.txt", 'a')

    try:
        
        a = float(input("Podaj 1 liczbe: ").replace(",","."))
        b = float(input("Podaj 2 liczbe: ").replace(",","."))

        operation = input("Wybierz operacje (wpisz: +,-,* lub /): ").strip()

      
            
        
    except ValueError as e:

        error = "ValueError: Wpisane dane sa niepoprawne. \n"
        print(e)
        file.write(e)

            
        
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

                error = "ZeroDivisionError: Nie mozna dzielic przez 0. \n"
                print(error)
                file.write(error)

        else:

            error = "Wprowadzono niepoprawny znak operacji. \n"
            print(error)
            file.write(error)
        
    finally:
            
        print("Kolejna operacja...")
        file.close()

