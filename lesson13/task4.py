import sqlite3


conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''

SELECT 
    AVG(p.cena) AS srednia
FROM Produkty p
JOIN Kategorie k
    ON p.id_kategorii = k.id_kategorii
WHERE k.nazwa_kategorii = 'Książki'

'''

cursor.execute(query)
wynik = cursor.fetchone()

print("Średnia cena produktów z kategorii Książki:", wynik[0])

conn.close()