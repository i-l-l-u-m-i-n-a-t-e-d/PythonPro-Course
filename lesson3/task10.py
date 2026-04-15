def oblicz_pole_prostokata(a, b):
    
    # Tutaj dodaj docstring
    
    """ This function takes two non-negative numbers and calculates the area of a rectangle. """
    
    # calculating the area of that rectangle
    pole = a * b
    
    # returns the value
    return pole

bok_a = 10
bok_b = 20

if bok_a > 0 and bok_b > 0:
    
    wynik = oblicz_pole_prostokata(bok_a, bok_b)
    print(f"Pole prostokąta o bokach {bok_a} i {bok_b} wynosi {wynik}.")

else: 
    
    print("Wprowadzono niepoprawne dane.")
