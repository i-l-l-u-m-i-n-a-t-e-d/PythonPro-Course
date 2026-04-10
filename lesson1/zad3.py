height = float(input("Podaj dlugosc prostokata: ".replace(",",".")))
width = float(input("Podaj szerokosc prostokata: ".replace(",",".")))

error = False
if height < 0:
    print("Dlugosc nie moze byc ujemna.")
    error = True
    
elif width < 0: 
    print("Szerokosc nie moze byc ujemna.")
    error = True
else:
    
    circuit = 2*(height+width)

    print(f"Obwod tego prostokata to {circuit}")

