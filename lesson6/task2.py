oceny = {"Jan": 4, "Anna": 5, "Piotr": 3, "Kasia": 4}

by_grades = sorted(oceny, key=lambda grades: grades[0]) 

dict = {}

for i in by_grades:

    dict[i] = oceny[i]


print(dict)
