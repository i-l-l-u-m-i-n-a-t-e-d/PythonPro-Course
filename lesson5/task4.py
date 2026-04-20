POZIOM_DOSTEPU = "user"

def local_function():

    POZIOM_DOSTEPU = "admin"   # local var

    print("Wewnatrz funkcji ", POZIOM_DOSTEPU)

local_function()

print("Na zewnatrz funkcji ", POZIOM_DOSTEPU)










