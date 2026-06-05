name_surname = input("Wpisz swoje imię i nazwisko: ")

clean_name_surname = name_surname.strip()
formatted_name_surname = clean_name_surname.title()
name_surname_length = len(formatted_name_surname)

print(f"Sformatowane dane: {formatted_name_surname}")
print(f"Długość sformatowanych danych: {name_surname_length}")
