sekret = 42

while True:

    try:
        number = int(input("Podaj liczbe: "))

        if number == sekret:
            
            print("Gratulacje!")
            break
        
        else:
            print("To nie ta liczba.")

    except ValueError:
        
        print("Wpisane dane to nie liczba.")
      

  

    

