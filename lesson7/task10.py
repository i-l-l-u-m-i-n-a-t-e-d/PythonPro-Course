def task10(name: str):

    r = 0.0

    try:
        
        with open(f"{name}", "r") as file:
        
            for line in file:

                try:
                    
                    #print(line)
                    r += float(line)

            
                except ValueError:

                    pass
                
                
            

    except FileNotFoundError:
        
        print("Nie znaleziono pliku.")
    
    finally:

        print(r)


file_name = input("Podaj nazwe pliku (nazwa.rozszerzenie): ").strip()

task10(file_name)

    

