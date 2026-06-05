a = int("256")
b = int("256")
c = int("256")

print(f"Id zmiennej a: {id(a)}")
print(f"Id zmiennej b: {id(b)}")
print(f"Id zmiennej c: {id(c)}")

print(f"a is b: {a is b}")
print(f"b is c: {b is c}")

d = int("257")
e = int("257")
f = int("257")

print(f"Id zmiennej d: {id(d)}")
print(f"Id zmiennej e: {id(e)}")
print(f"Id zmiennej f: {id(f)}")

print(f"d is e: {d is e}")
print(f"e is f: {e is f}")

# dla 256 Python zwykle pokazuje ten sam id, bo małe liczby są trzymane w pamięci
# przy 257 może być inaczej, bo ta liczba nie mieści się już w tym standardowym zakresie
