import sqlite3

conn = sqlite3.connect('biblioteka.db')
c = conn.cursor()

c.execute("SELECT * FROM ksiazki")

all_data = c.fetchall()

for i in all_data:
    
    print(i)
    
conn.close()