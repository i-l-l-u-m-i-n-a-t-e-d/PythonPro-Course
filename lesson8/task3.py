import json

konfiguracja = {
    
    "użytkownik": "admin", 
    "motyw": "ciemny", 
    "rozdzielczość": [1920, 1080]
    
}

with open("config.json", "w", encoding="utf-8") as file:

    json.dump(konfiguracja, file, indent=4, ensure_ascii=False)

