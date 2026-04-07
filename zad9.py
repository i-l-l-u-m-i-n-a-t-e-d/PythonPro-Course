import this
import codecs

zen = codecs.decode(this.s, "rot_13")

dane = zen.split()

r=""

for v in dane[7:17]:
    r += v + " "

print(r)




