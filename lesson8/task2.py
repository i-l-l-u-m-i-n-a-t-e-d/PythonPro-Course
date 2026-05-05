file_name = input("Podaj nazwe pliku (nazwa.rozszerzenie): ").strip()

words = 0

try:
        
    
    with open(f"{file_name}", "r") as file:
        
        for line in file:

            sep_line = line.split()
            words += len(sep_line)


        
except FileNotFoundError:
        
    print("Nie znaleziono pliku.")


print(f"Liczba slow w tym pliku to: {words}")
    

