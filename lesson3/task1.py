a = float(input("Podaj pierwszą liczbę: ").replace(",","."))
b = float(input("Podaj drugą liczbę: ").replace(",","."))

print(f"Wynik dodawania: {a+b}")
print(f"Wynik odejmowania: {a-b}")

multi = a*b

print(f"Wynik mnozenia: {multi}")

if b == 0:

    print("Nie można dzielić przez 0.")

else:
    
    divide = a/b
    print(f"Wynik dzielenia: {divide}")