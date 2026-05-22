import sqlite3

conn = sqlite3.connect('sklep.db')
cursor = conn.cursor()

query = '''
SELECT Produkty.nazwa_produktu
FROM Klienci
JOIN Zamowienia ON Klienci.id_klienta = Zamowienia.id_klienta
JOIN Zamowienia_Produkty ON Zamowienia.id_zamowienia = Zamowienia_Produkty.id_zamowienia
JOIN Produkty ON Zamowienia_Produkty.id_produktu = Produkty.id_produktu
WHERE Klienci.imie = 'Anna Nowak';
'''

cursor.execute(query)
wyniki = cursor.fetchall()

for wiersz in wyniki:
    print(wiersz[0])

conn.close()