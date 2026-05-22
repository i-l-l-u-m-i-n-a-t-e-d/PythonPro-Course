import sqlite3

conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT 
    Kategorie.nazwa_kategorii,
    COUNT(Produkty.id_produktu) AS liczba_produktow
FROM Kategorie
LEFT JOIN Produkty
    ON Kategorie.id_kategorii = Produkty.id_kategorii
GROUP BY Kategorie.nazwa_kategorii;
'''

cursor.execute(query)
wyniki = cursor.fetchall()

for wiersz in wyniki:
    print(f"Kategoria: {wiersz[0]}, liczba produktów: {wiersz[1]}")

conn.close()