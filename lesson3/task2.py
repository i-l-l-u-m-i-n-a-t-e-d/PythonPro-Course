a=256
b=256
c=256

print(f"Id zmiennej a: {id(a)}")
print(f"Id zmiennej b: {id(b)}")
print(f"Id zmiennej c: {id(c)}")

d=257
e=257
f=257

print(f"Id zmiennej d: {id(d)}")
print(f"Id zmiennej e: {id(e)}")
print(f"Id zmiennej f: {id(f)}")

#ta sama wartosc zmiennych sprawia ze Python traktuje je tak samo i dlatego kazda trojka ma to samo id
