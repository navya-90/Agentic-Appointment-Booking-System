import sqlite3

conn = sqlite3.connect("appointments.db")
cursor = conn.cursor()

cursor.execute("SELECT * FROM appointments")
rows = cursor.fetchall()

for row in rows:
    print(row)

conn.close()
