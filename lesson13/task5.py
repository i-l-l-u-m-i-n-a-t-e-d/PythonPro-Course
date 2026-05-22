import sqlite3

conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT imie, email
FROM Klienci;
'''

cursor.execute(query)
wyniki = cursor.fetchall()

for klient in wyniki:
    print(f"{klient[0]} - {klient[1]}")

conn.close()