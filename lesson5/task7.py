def analiza_listy(lista: list[int]) -> tuple:

    minimum = min(lista)
    maximum = max(lista)
    suma = sum(lista)

    return minimum, maximum, suma #tuple


result = analiza_listy([1,2,10,15,-4,3,7,123])

print(result)