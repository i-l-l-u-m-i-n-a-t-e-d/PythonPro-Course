import sqlite3

conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT COUNT(*) 
FROM Produkty;
'''

cursor.execute(query)
wynik = cursor.fetchone()

print("Liczba wszystkich produktów:", wynik[0])

conn.close()