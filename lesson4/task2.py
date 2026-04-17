def data_val(i):

    validation = ("tak", "nie")

    r = 0

    for j in validation:

        if i == j:
            r += 1
    
    if r == 0:
        return False
    
    
    return True


status = input("Czy jestes studentem? (wpisz tak/nie) ").lower()
age = int(input("Ile masz lat? (wpisz tylko cyfry) "))


if data_val(status):

    
    if status == "tak" or age < 18:

        print("Cena biletu wynosi 50 PLN.")
    
    elif status =="nie" and age < 18:

        print("Cena biletu wynosi 50 PLN.")
    
    else:

        print("Cena biletu wynosi 100 PLN.")

else:

    print("Niepoprawnie odpowiedziano na pytanie o status studenta.")









