found_lines = []

try:
    word = input("Wpisz szukane slowo: ").strip()

    with open("log.txt", "r", encoding="utf-8") as file:
        
        for line in file:
            
            if word in line:
                
                found_lines.append(line)

except FileNotFoundError:
    
    print("Nie znaleziono pliku.")

except PermissionError:
    
    print("Nieuprawniony dostep.")

with open("wyniki_wyszukiwania.txt", "w", encoding="utf-8") as file2:
    
    for line in found_lines:
        
        file2.write(line)