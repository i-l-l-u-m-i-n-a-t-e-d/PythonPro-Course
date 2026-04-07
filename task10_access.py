print("Podaj swoj wzrost (tylko cyfry) [cm]: ")
wzrost = int(input())

print("Czy jest opiekun? (wpisz tak/nie): ")
opiekun = input()

op = True

if opiekun.lower() == 'nie':
    op = False

if (wzrost >= 120 and op == True) or wzrost >= 160:
    print("True")
else:
    print("False")
    