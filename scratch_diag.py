import sqlite3

def main():
    conn = sqlite3.connect('automail.db')
    cur = conn.cursor()
    try:
        cur.execute("""
            SELECT source, COUNT(*), SUM(CASE WHEN name='Hiring Manager' THEN 1 ELSE 0 END) AS generic_count
            FROM contacts GROUP BY source;
        """)
        rows = cur.fetchall()
        print("Source | Count | Generic Count")
        print("-" * 40)
        for r in rows:
            print(f"{r[0]} | {r[1]} | {r[2]}")
    except Exception as e:
        print("Error running query:", e)
    finally:
        conn.close()

if __name__ == '__main__':
    main()
