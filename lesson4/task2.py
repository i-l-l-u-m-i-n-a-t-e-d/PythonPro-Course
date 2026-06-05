def data_val(i):

    validation = ("tak", "nie")

    if i in validation:
        return True

    return False


base_price = 100

status = input("Czy jestes studentem? (wpisz tak/nie) ").lower()
age = int(input("Ile masz lat? (wpisz tylko cyfry) "))

if data_val(status) and age >= 0:

    if status == "tak" or age < 18:
        price = base_price * 0.5

    else:
        price = base_price

    print(f"Cena biletu wynosi {price} PLN.")

else:

    print("Niepoprawnie podano dane.")
