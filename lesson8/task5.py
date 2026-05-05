import csv

produkty = [

    {"nazwa": "Mleko", "cena":3.50}, 
    {"nazwa": "Chleb", "cena": 4.20}
    
]

values = []

for i in range(len(produkty)):
    sub_list = []
    for j in produkty[i]:
            
            #print(produkty[i][j]) values
            sub_list.append(produkty[i][j])
            
    values.append(sub_list)
    #print(sub_list)

#nazwa, cena - columns

with open("produkty.csv", "w",newline="", encoding="utf-8") as file:

    writing = csv.writer(file, delimiter=", ")
    writing.writerow(["nazwa", "cena"])
    writing.writerows(values) 
       
    



           
        
       
    