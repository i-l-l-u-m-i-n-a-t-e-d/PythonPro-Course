import sqlite3

conn = sqlite3.connect('uczelnia.db')
c = conn.cursor()

studenci_lista = [

    (1, 'Jan', 'Ziemniak'),
    (2, 'Robert', 'Mróz'),
    (3, 'Adam', 'Kopernik'),
    (4, 'Anna', 'Lato')

]

audytoria_lista = [

    (1, 'B4', 122),
    (2, 'A0', 123),
    (3, 'A1', 222)

]

c.executemany(

    "INSERT INTO studenci (id_studenta, imie, nazwisko) VALUES (?, ?, ?)",
    studenci_lista
)

c.executemany(
    
    "INSERT INTO audytoria (id_audytorium, nazwa_budynku, numer_sali) VALUES (?, ?, ?)",
    audytoria_lista
)

conn.commit()

print(f"Dodano {len(studenci_lista)} rekordy do tabeli studenci")
print(f"Dodano {len(audytoria_lista)} rekordy do tabeli audytoria")

conn.close()