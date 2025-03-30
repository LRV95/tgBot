import sqlite3
import os

def check_database():
    db_path = os.path.join('database', 'database.db')
    print(f"Checking database at: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")
    
    if not os.path.exists(db_path):
        print("Database file not found!")
        return
        
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Проверяем таблицу events
        cursor.execute("SELECT * FROM events")
        events = cursor.fetchall()
        print(f"\nFound {len(events)} events:")
        for event in events:
            print(f"\nEvent ID: {event[0]}")
            print(f"Name: {event[1]}")
            print(f"Date: {event[2]}")
            print(f"Time: {event[3]}")
            print(f"City: {event[4]}")
            print(f"Description: {event[6]}")
            print(f"Tags: {event[9]}")
            
        conn.close()
        
    except Exception as e:
        print(f"Error checking database: {e}")

if __name__ == "__main__":
    check_database() 