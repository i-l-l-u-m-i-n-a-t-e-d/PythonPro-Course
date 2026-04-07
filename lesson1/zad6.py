prawo=input("Czy masz prawo jazdy (wpisza tak/nie)? ").lower()
wiek= int(input("Ile masz lat (tylko cyfry) ? "))

checker = False

if wiek >= 18 and prawo == 'tak':
    print(not checker)

else:
    print(checker)
          
