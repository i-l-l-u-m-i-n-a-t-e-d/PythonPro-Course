try:
    
    with open("nieistniejacy.txt", "r") as file:
        
        for i in file:
            
            print(i)
    
except FileNotFoundError:
    
    print("Nieznaleziono pliku.")