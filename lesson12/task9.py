import sqlite3

conn = sqlite3.connect("uczelnia.db")
c = conn.cursor()

c.execute("SELECT id_studenta FROM studenci")
studenci = c.fetchall()

c.execute("SELECT id_audytorium FROM audytoria")
audytoria = c.fetchall()

przypisania = []

for index, student in enumerate(studenci):

    id_studenta = student[0]

    id_audytorium = audytoria[index % len(audytoria)][0]

    przypisania.append((id_studenta, id_audytorium))

c.executemany(

    "INSERT INTO przypisania (id_studenta, id_audytorium) VALUES (?, ?)",
    przypisania
    
)

conn.commit()

print(f"Dodano {len(przypisania)} przypisania.")

conn.close()