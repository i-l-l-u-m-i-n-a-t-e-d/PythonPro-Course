import sqlite3

conn = sqlite3.connect('biblioteka.db')
c = conn.cursor()

year_of_release = 1900
autor = 'Ernest Hemingway'

c.execute(

    "UPDATE ksiazki SET rok_wydania = ? WHERE autor = ?",
    (year_of_release, autor)
)

conn.commit()

print("Zmieniono")

c.execute(

    "SELECT tytul, autor, rok_wydania FROM ksiazki WHERE autor = ?",
    (autor,)
)

all_data = c.fetchall()

for i in all_data:
    
    print(i)

conn.close()