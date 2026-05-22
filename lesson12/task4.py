import sqlite3

conn = sqlite3.connect('biblioteka.db')
c = conn.cursor()

c.execute("SELECT tytul, autor, rok_wydania FROM ksiazki WHERE autor = 'Ernest Hemingway'")

all_data = c.fetchall()

for i in all_data:
    
    print(i)
    
conn.close()