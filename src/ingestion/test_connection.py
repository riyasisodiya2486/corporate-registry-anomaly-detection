import psycopg2

DB_CONFIG = {
    "host": "localhost",
    "port": 5432,
    "dbname": "registry",
    "user": "admin",
    "password": "admin123",
}


def test_connection():
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("PostgreSQL connection successful.")
        conn.close()
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")


if __name__ == "__main__":
    test_connection()