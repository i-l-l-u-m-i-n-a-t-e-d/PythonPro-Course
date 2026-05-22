import sqlite3

conn = sqlite3.connect('uczelnia.db')
c = conn.cursor()

print("Polaczono z baza danych!")

c.execute('''
          
    CREATE TABLE IF NOT EXISTS studenci (
        id_studenta INTEGER PRIMARY KEY,
        imie TEXT NOT NULL,
        nazwisko TEXT NOT NULL
    )
          
''')

print("Tabela studenci zostala utworzona.")

c.execute('''
          
    CREATE TABLE IF NOT EXISTS audytoria (
        id_audytorium INTEGER PRIMARY KEY,
        nazwa_budynku TEXT NOT NULL,
        numer_sali INTEGER
    )
          
''')

conn.commit()

print("Tabela audytoria zostala utworzona.")

conn.close()