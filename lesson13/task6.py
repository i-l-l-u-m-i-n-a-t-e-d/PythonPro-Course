import sqlite3

conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT nazwa_produktu, cena
FROM Produkty
WHERE cena > (
    SELECT AVG(cena)
    FROM Produkty
);
'''

cursor.execute(query)
wyniki = cursor.fetchall()

for produkt in wyniki:
    print(f"{produkt[0]} - {produkt[1]}")

conn.close()


