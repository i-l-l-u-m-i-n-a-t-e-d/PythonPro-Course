import sqlite3

conn = sqlite3.connect('biblioteka.db')
c = conn.cursor()


dane = [

    (1, 'Stary człowiek i morze', 'Ernest Hemingway', '1952'),
    (2, 'Urwisko', 'Remigiusz Mróz', '2026'),
    (3, 'Quo Vadis', 'Henryk Sienkiewicz', '1896')
]

c.executemany(
    
    "INSERT INTO ksiazki (id, tytul, autor, rok_wydania) VALUES (?, ?, ?, ?)",
    dane
)

conn.commit()

print(f"Dodano {c.rowcount} rekordy do tabeli ksiazki")


conn.close()
      