import csv

r = 0

with open("produkty.csv", "r",newline="", encoding="utf-8") as file:

    reader = csv.DictReader(file, delimiter=" ", fieldnames=['nazwa','cena'])
    
    for i in reader:
        
        try:
            
            r += float(i["cena"])
        
        except ValueError:
            pass
        
print(f"Suma cen to: {r}")
