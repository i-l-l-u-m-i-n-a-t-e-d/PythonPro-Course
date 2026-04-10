prawo=input("Czy masz prawo jazdy (wpisza tak/nie)? ").lower()
wiek= int(input("Ile masz lat (tylko cyfry) ? "))


if wiek >= 18 and prawo == 'tak':
    print(True)

else:
    print(False)
          
