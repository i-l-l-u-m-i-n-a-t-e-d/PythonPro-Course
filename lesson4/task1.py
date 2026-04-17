age = int(input("Podaj wiek (wpisz tylko cyfry) w latach: "))

if age >= 0 and age <= 1:

    print("Niemowlę")

elif age >= 2 and age <= 12:
    
    print("Dziecko")

elif age >= 13 and age <= 17:
    
    print("Nastolatek")

elif age >= 18 and age <= 64:
    
    print("Dorosły")

else: 
    
    print("Senior")