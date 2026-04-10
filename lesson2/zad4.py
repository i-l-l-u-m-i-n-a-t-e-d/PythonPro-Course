import datetime

n = datetime.datetime.now()

year = n.year

name = input("Podaj swoje imię: ").capitalize()
year_of_birth = int(input("Podaj swój rok urodzenia (tylko cyfry): "))

error = False
if len(str(year_of_birth)) != 4:
    error=True
    print("Wpisałeś niepoprawny rok urodzenia.")

if not error:
    print(f"Cześć, {name}! W 2027 roku będziesz mieć  {year+1 - year_of_birth} lat.")