def czy_pierwsza(n):

    dividers = False

    if n == 1:
        dividers = True

    for i in range(2, n):

        if n % i == 0:

            dividers = True
            break
    
    if dividers:

        return False
    
    return True

numbers = [i for i in range(1, 31)]

result = list(filter(lambda x: czy_pierwsza(x), numbers))

print(result)