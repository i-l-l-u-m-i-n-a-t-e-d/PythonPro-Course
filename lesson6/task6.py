def stworz_licznik():
    
    licznik = 0

    def local_function():

        nonlocal licznik
        licznik += 1
      
        return licznik

    return local_function


licznik = stworz_licznik()


print(licznik())
print(licznik())
print(licznik())

