import json

with open("config.json","r",encoding="utf-8") as file:

    dane = json.load(file)


print(f"Witaj, {dane["użytkownik"]}! Twój motyw to {dane["motyw"]}.")
