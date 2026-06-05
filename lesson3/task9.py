x = 10

print(id(x))

x = x + 1

print(id(x))

# id sie zmienilo, bo po dodaniu 1 x ma juz inna wartosc
# Python tworzy nowy obiekt dla 11, zamiast zmieniac stare 10
