import psycopg2
import random
import os
from urllib.parse import urlparse

def seed_database():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set, skipping seeding")
        return
    parsed = urlparse(database_url)
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/')
    )
    cursor = conn.cursor()
    # Create table if not exists
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS test_data (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255),
            value INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    # Insert random data
    for _ in range(10):  # Insert 10 random rows
        name = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=10))
        value = random.randint(1, 1000)
        cursor.execute("INSERT INTO test_data (name, value) VALUES (%s, %s)", (name, value))
    conn.commit()
    cursor.close()
    conn.close()
    print("Database seeded with test data")

if __name__ == "__main__":
    seed_database()
