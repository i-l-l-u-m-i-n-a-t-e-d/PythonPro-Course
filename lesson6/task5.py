from functools import reduce

one_five = [1, 2, 3, 4, 5]

result = reduce(lambda x, y: x*y, one_five)

print(result)