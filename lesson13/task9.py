import sqlite3

def znajdz_produkty_w_kategorii(nazwa_kategorii):
    
    conn = sqlite3.connect('sklep.db')
    cursor = conn.cursor()

    query = '''
    SELECT 
        Produkty.nazwa_produktu,
        Produkty.cena
    FROM Produkty
    JOIN Kategorie
        ON Produkty.id_kategorii = Kategorie.id_kategorii
    WHERE Kategorie.nazwa_kategorii = ?;
    '''

    cursor.execute(query, (nazwa_kategorii,))
    wyniki = cursor.fetchall()

    conn.close()

    return wyniki


produkty = znajdz_produkty_w_kategorii('Elektronika')

print(produkty)