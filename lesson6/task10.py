uzytkownicy = [
{"imie": "Jan", "wiek": 30, "aktywny": True},
{"imie": "Anna", "wiek": 17, "aktywny": False},
{"imie": "Piotr", "wiek": 25, "aktywny": True}
]


result = [uzytkownicy[i]["imie"] for i in range(len(uzytkownicy)) if uzytkownicy[i]["wiek"] > 18 and uzytkownicy[i]["aktywny"]]

print(result)


