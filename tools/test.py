import sqlite3

conn = sqlite3.connect('C:/Users/madsu/PycharmProjects/PythonProject2/news.db')
cursor = conn.cursor()

cursor.execute("""
    SELECT id, title, source, created_at
    FROM news
    ORDER BY created_at DESC
""")

rows = cursor.fetchall()

for row in rows:
    print("-" * 80)
    print("ID:", row[0])
    print("Title:", row[1])
    print("Source:", row[2])
    print("Created:", row[3])

conn.close()