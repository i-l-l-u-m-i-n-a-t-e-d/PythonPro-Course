kursy = {"USD": 4.0, "EUR": 4.3}

def conti():

    c = input("Chcesz kontynuowac (wpisz tak/nie)? ").strip().lower()

    if c == "nie":

        return False

    return True    

while True:

    try:
        #value
        amount = float(input("Podaj kwotę w PLN: ").replace(",","."))

        #key
        currency = input("Wpisz kod waluty (USD lub EUR): ").strip().upper() 

        if currency == "USD":

            r = amount/kursy[currency]

            print(f"Tyle PLN to tyle USD: {r:.2f} ")
            
            if conti() is False:
                break
           
        
        elif currency == "EUR":
             
            r = amount/kursy[currency]

            print(f"Tyle PLN to tyle w EUR: {r:.2f} ")
            
            if conti() is False:
                
                break
            
        
        else:
            print("Nie posiadam kursu tej waluty.")

            if conti() is False:
                
                break
            



    except ValueError:

        print("Wpisano niepoprawne dane.")

        if conti() is False:
                
                break