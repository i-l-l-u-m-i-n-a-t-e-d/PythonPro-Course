import sqlite3

conn = sqlite3.connect('biblioteka.db')

c = conn.cursor()

print("Polaczono z baza danych!")


c.execute('''
    
    CREATE TABLE IF NOT EXISTS ksiazki(
        
        id INTEGER PRIMARY KEY,
        tytul TEXT NOT NULL,
        autor TEXT NOT NULL,
        rok_wydania INTEGER 
    )
    
    
''')

conn.commit()

print("Tabela ksiazka zostala utworzona.")

conn.close()