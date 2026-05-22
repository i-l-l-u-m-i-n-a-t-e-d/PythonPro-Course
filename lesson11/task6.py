class InvalidPasswordError(Exception):
    pass


def ustaw_haslo(haslo):

    if len(haslo) < 8:

        raise InvalidPasswordError("Hasło musi mieć co najmniej 8 znaków.")

    return True


try:
    ustaw_haslo("Pass")

except InvalidPasswordError as e:
    
    print(e)

else:
    print("Hasło zostało ustawione poprawnie.")