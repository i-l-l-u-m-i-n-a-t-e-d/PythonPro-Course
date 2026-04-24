numbers = [-5, 2, 8, -1, 0, 10]

result = list(map(lambda x: pow(x,2),filter(lambda x: x >= 0, numbers)))

print(result)