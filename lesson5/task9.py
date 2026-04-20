def silnia(n: int) -> int:

    
    if n == 0:

        return 1
    
    return n * silnia(n-1)


result = silnia(5)


print(result)