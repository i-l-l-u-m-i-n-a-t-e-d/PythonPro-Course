def age_of_dog_conv(age):
    
    if age == 1:
        r = 15
        
    elif age == 2:
        r = 15 + 9
        
    else:
        r = 15 + 9 + (age - 2) * 5
    
    return r


age = int(input("Podaj wiek psa (wpisz tylko cyfry): "))

if age <= 0:
    print("Wiek psa musi być większy od 0.")
    
else:
    result = age_of_dog_conv(age)

    print(f"Wiek tego psa w ludzkich latach to: {result}")
