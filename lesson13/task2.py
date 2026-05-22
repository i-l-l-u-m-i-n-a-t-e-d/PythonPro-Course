import sqlite3

conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT nazwa_produktu, cena
FROM Produkty
WHERE cena = (
    SELECT MAX(cena)
    FROM Produkty
);
'''

cursor.execute(query)
wynik = cursor.fetchone()

print("Najdroższy produkt:", wynik[0])
print("Cena:", wynik[1])

conn.close()