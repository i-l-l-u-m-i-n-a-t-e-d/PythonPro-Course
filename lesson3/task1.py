a = float(input("Podaj pierwszą liczbę: ").replace(",", "."))
b = float(input("Podaj drugą liczbę: ").replace(",", "."))

print(f"Pierwsza liczba: {a}")
print(f"Typ pierwszej liczby: {type(a)}")
print(f"Identyfikator pierwszej liczby: {id(a)}")

print(f"Druga liczba: {b}")
print(f"Typ drugiej liczby: {type(b)}")
print(f"Identyfikator drugiej liczby: {id(b)}")

dodawanie = a + b
odejmowanie = a - b
mnozenie = a * b

print(f"Wynik dodawania: {dodawanie}")
print(f"Wynik odejmowania: {odejmowanie}")
print(f"Wynik mnożenia: {mnozenie}")

if b == 0:
    print("Nie można dzielić przez 0.")
else:
    dzielenie = a / b
    print(f"Wynik dzielenia: {dzielenie}")
