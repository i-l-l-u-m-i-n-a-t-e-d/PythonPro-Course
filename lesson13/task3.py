import sqlite3


conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT 
    SUM(Produkty.cena) AS laczna_wartosc_elektroniki
FROM Produkty
JOIN Kategorie
    ON Produkty.id_kategorii = Kategorie.id_kategorii
WHERE Kategorie.nazwa_kategorii = 'Elektronika';
'''

cursor.execute(query)
wynik = cursor.fetchone()

print("Łączna wartość produktów z kategorii Elektronika:", wynik[0])

conn.close()