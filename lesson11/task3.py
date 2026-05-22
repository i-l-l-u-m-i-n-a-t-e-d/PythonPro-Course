class KalkulatorWalut:
    
    #1 USD = 4.0 PLN
    
    @staticmethod
    def usd_na_pln(usd: float):
        
        return f"Podana kwota w $ to {usd*4.0} PLN. Kurs 1 USD = 4.0 PLN."
    
    

r = KalkulatorWalut.usd_na_pln(135)

print(r)
    
    