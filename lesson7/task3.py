def open_file(name: str):
    
    try:
        
        file = open(f"{name}", "r")
        
        file_content = file.read()
        
        print(file_content)
        
        
            
    except FileNotFoundError:
        
        print("Nie znaleziono pliku.")
    
    except PermissionError:
        
        print("Nieuprawniony dostep.")
    
    finally:

        file.close()


open_file("task3.txt")