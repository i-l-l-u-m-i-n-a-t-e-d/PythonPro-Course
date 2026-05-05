import json

id = 0

def display():
    
    try: 
        
        with open("zadania.json", "r", encoding="utf-8") as file:

            tasks = json.load(file)
            
            print("Obecna lista zadań. \n")
            
            for i in tasks:
                
                for j in i:
                    
                    if type(i[j]) is bool:
                    
                        if i[j]:
                        
                            print("Zadanie ukończone.")
                    
                        else:
                        
                            print("Zadanie nieukończone")
                        
                
                    else:
                        
                        if type(i[j]) is int:
                            
                            global id
                            id = i[j]
                        
                        print(i[j])
    
    except FileNotFoundError:
       
        print("Nieznaleziono pliku.")
    
    file.close()
    

                    
def add(title: str, description: str, completed: bool):
    
    global id
    
    data = {
            
            "id": id+1,
            "title": title,
            "description": description,
            "completed": completed
            
        }
    
    with open("zadania.json", "r+", encoding="utf-8") as file:
        
        tasks = json.load(file)

        tasks.append(data)

        file.seek(0)
        json.dump(tasks, file, ensure_ascii=False, indent=4)
        


display() #first step



while True:
        
    decision = input("\n Jesli chcesz: \n -dodac nowe zadanie, wpisz 'dodaj' \n -wyswietlic wszystkie zadania, wpisz 'wyswietl' \n -zapisac aktualna liste zadan, wpisz 'zapisz' \n").strip().lower()

    if decision == "dodaj":
        
        title = input("Wpisz tytul zadania: ").strip().capitalize()
        description = input("Wpisz opis zadania: ").capitalize()
        
        completed = input("Czy zadanie zostalo ukonczone? (wpisz tak/nie)").strip().lower()
        
        if completed == "tak":
            
            add(title=title, description=description, completed=True)
            
        elif completed == "nie":
            
            add(title=title, description=description, completed=False)
            
        else:
            
            print("Nie udalo sie okreslic czy zadanie zostalo ukonczone, wpisano niepoprawne dane.")
            
       
    
    elif decision == "wyswietl":
    
        display()
    
    elif decision == "zapisz":
        
        break
    
    else:
        
        print("Nieudalo sie okreslic jakie dzialanie wybrano, wprowadzono niepoprawne dane. ")


  
    
  

