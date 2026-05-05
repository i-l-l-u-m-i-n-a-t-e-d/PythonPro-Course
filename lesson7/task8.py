# Definiujemy własny typ błędu
class BladWalidacjiError(Exception):

    """Wyjątek zgłaszany, gdy hasło nie spełnia wymagań."""
    pass

def sprawdz_haslo(haslo: str):

    error_list = []
    if len(haslo) < 8:
        
        error_list.append("Hasło jest za krótkie (minimum 8 znaków).")
    
    if not any(char.isdigit() for char in haslo):
        
        error_list.append("Hasło musi zawierać co najmniej jedną cyfrę.")
    
    
    if len(error_list) > 0:

        raise BladWalidacjiError(error_list)


    print("Hasło jest poprawne.")


try:

    sprawdz_haslo("za-kr")

except BladWalidacjiError as e:

    print(f"Lista bledow: {e}")

