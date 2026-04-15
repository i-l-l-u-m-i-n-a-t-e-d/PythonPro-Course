def oblicz_pole_prostokata(a, b):
    
    # Tutaj dodaj docstring
    
    """ Ta funkcja przyjmuje 2 liczby nieujemne i oblicza pole powierzchni prostokąta. """
    
    # Tutaj dodaj komentarz
    pole = a * b
    
    # Tutaj dodaj komentarz
    return pole

bok_a = 10
bok_b = 20

if bok_a > 0 and bok_b > 0:
    
    wynik = oblicz_pole_prostokata(bok_a, bok_b)
    print(f"Pole prostokąta o bokach {bok_a} i {bok_b} wynosi {wynik}.")

else: 
    
    print("Wprowadzono niepoprawne dane.")