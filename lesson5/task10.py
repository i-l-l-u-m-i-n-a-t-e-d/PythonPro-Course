def sprawdz_haslo(haslo: str) -> bool:

    """
    Function checks if provided string contains:
        
        -at least 8 characters
        -one upper letter
        -at least one digit

        and returns True/False
    
    """
    
    length: int = len(haslo)
    big_letter: bool = False
    digit: bool = False

    
    for i in haslo:

        if i.isupper():

            big_letter = True
            #break

        if i.isdigit():

            digit = True

            if big_letter:
                break

        
    if length >= 8 and big_letter and digit:

        return True
    
    return False

print(sprawdz_haslo("Ąslowww####1"))