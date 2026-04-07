print("Podaj pierwsza liczbe: ")
a=float(input())

print("Podaj druga liczbe: ")
b=float(input())

print("Jakie dzialanie chcesz wykonac (wpisz ktorys z tych znakow: + , - , * , / ): ")
z=input()

if z == '+':
    print(f"Wynik dodawania: {a+b}")

elif z == '-':
    print(f"Wynik odejmowania: {a-b}")

elif z == '*':
    print(f"Wynik mnozenia: {a*b}")

elif z == '/':
    if b == 0:
        print("Nie mozna dzielic przez 0.")
    else:
        print(f"Wynik dzielenia: {a/b}")
else:
    print("Wpisales niepoprawny znak")



