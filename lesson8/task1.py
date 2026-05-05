while True:

                
    line = input("Wpisz linie tekstu ktora chcesz dodac do pliku (wpisz koniec jesli chcesz przerwac): ")

   

    if len(line.strip()) == 0:
        
        print("Nic nie wpisano.")
        continue
    
    if line.strip().lower() == "koniec":

        break

    
    try:
            
        with open("dziennik.txt", 'a', encoding="utf-8") as file:

            file.writelines(line.strip()+"\n")

            


            
    except FileNotFoundError:
            
        print("Nie znaleziono pliku.")
        
    except PermissionError:
            
        print("Nieuprawniony dostep.")
    
   


