import sqlite3

def znajdz_sale_studenta(nazwisko):

    conn = sqlite3.connect('uczelnia.db')
    c = conn.cursor()

    c.execute('''
              
        SELECT 
            studenci.imie,
            studenci.nazwisko,
            audytoria.nazwa_budynku,
            audytoria.numer_sali
        FROM studenci
        JOIN przypisania
            ON studenci.id_studenta = przypisania.id_studenta
        JOIN audytoria
            ON przypisania.id_audytorium = audytoria.id_audytorium
        WHERE studenci.nazwisko = ?
              
    ''', (nazwisko,))

    wynik = c.fetchone()

    if wynik:

        imie, nazwisko, budynek, sala = wynik

        print(f"{imie} {nazwisko} znajduje się w budynku {budynek}, sala {sala}.")
    
    else:
        
        print("Nie znaleziono studenta o takim nazwisku.")

    conn.close()


znajdz_sale_studenta("Ziemniak")