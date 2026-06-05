p = bool(int(input("Wprowadź 1 wartość logiczną (0 - False, 1 - True): ")))
q = bool(int(input("Wprowadź 2 wartość logiczną (0 - False, 1 - True): ")))

and_op = p and q
or_op = p or q

print(f"Wynik AND: {and_op}")
print(f"Wynik OR: {or_op}")
