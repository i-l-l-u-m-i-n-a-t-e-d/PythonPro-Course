def age_of_dog_conv(age):
    
    r = 0
    
    for i in range(age):
        
        if i == 0:
            r += 15
        
        elif i == 1:
            r += 9
        
        else:
            r += 5
    
    return r


age = int(input("Podaj wiek psa (wpisz tylko cyfry): "))

result = age_of_dog_conv(age)

print(f"Wiek tego psa w ludzkich latach to: {result}")