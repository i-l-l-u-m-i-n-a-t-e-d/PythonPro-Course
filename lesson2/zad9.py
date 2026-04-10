p = int(input("Wprowadź 1 wartość logiczną (wpisz 0 lub 1, 0 - False, 1 - True): "))

q = int(input("Wprowadź 2 wartość logiczną (wpisz 0 lub 1, 0 - False, 1 - True): "))


and_op = p and q

or_op = p or q

if and_op:
    print("1 - True")

else:
    print("0 - False")


if or_op:
    print("1 - True")

else:
    print("0 - False")


