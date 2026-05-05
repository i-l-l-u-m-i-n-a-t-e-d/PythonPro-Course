class WiekNiepoprawnyError(Exception):

    pass



def rejestruj_uzytkownika(wiek: int):
    
    if not isinstance(wiek, int):
        
        raise TypeError("Wiek musi być liczbą całkowitą.")
    
    if wiek < 18:
        
        raise WiekNiepoprawnyError("Podano niepoprawny wiek.")

    
    
age = int(input("Podaj swoj wiek (wpisz tylko liczby): "))


try:

    rejestruj_uzytkownika(age)
    print("Wpisano poprawny wiek.")

except (TypeError, WiekNiepoprawnyError) as e:

    print("Wiek niepoprawny.")




    
  
    
    

