class Produkt:
    
    def __init__(self, name:str, price:float, category:str):
        
        self.name = name
        self.price = price
        self.category = category
        

product = Produkt("mleko", 4.55, "napoj")

print(product.name)    
print(product.price)  
print(product.category)      