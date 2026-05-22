def bezpieczne_dzielenie(a, b):
    
    try:
        
        r = a/b
        
        return r
    
    except ZeroDivisionError:
        
        print("Błąd: Dzielenie przez zero!")
        
        return None
    
    
print(bezpieczne_dzielenie(21,7))
print(bezpieczne_dzielenie(10,0))

