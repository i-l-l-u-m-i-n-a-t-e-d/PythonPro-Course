import sqlite3


class Produkt:
    def __init__(self, id_produktu, nazwa_produktu, cena):
        self.id_produktu = id_produktu
        self.nazwa_produktu = nazwa_produktu
        self.cena = cena

    def __str__(self):
        return f"{self.id_produktu}. {self.nazwa_produktu} - {self.cena} zł"


def pobierz_wszystkie_produkty():
    
    conn = sqlite3.connect('sklep.db')
    cursor = conn.cursor()

    query = '''
    SELECT 
        id_produktu,
        nazwa_produktu,
        cena
    FROM Produkty;
    '''

    cursor.execute(query)
    wyniki = cursor.fetchall()

    produkty = []

    for wiersz in wyniki:
        
        produkt = Produkt(wiersz[0], wiersz[1], wiersz[2])
        produkty.append(produkt)

    conn.close()

    return produkty


produkty = pobierz_wszystkie_produkty()

for produkt in produkty:
    print(produkt)