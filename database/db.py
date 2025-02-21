import sqlite3


class Database:
    def __init__(self, db_name='./database/database.db'):
        self.db_name = db_name
        self.create_tables()

    def connect(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def create_tables(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    first_name TEXT,
                    last_name TEXT,
                    email TEXT,
                    registered_events TEXT,
                    score INTEGER,
                    used_codes TEXT,
                    tags TEXT,
                    role TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT,
                    curator TEXT,
                    phone_number TEXT,
                    email TEXT,
                    description TEXT,
                    tags TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    event_date TEXT,
                    start_time TEXT,
                    participants_count INTEGER,
                    participation_points INTEGER,
                    creator TEXT,
                    tags TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    event_id INTEGER,
                    address TEXT,
                    district TEXT,
                    city TEXT,
                    province TEXT,
                    region TEXT,
                    responsible_institution TEXT,
                    FOREIGN KEY (project_id) REFERENCES projects(id),
                    FOREIGN KEY (event_id) REFERENCES events(id)
                )
            ''')
            conn.commit()

    def _format_project(self, row):
        return {
            "id": row[0],
            "name": row[1],
            "curator": row[2],
            "phone_number": row[3],
            "email": row[4],
            "description": row[5],
            "tags": row[6]
        }

    def _format_event(self, row):
        return {
            "id": row[0],
            "project_id": row[1],
            "event_date": row[2],
            "start_time": row[3],
            "participants_count": row[4],
            "participation_points": row[5],
            "creator": row[6],
            "tags": row[7]
        }

    def get_all_projects(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects")
            rows = cursor.fetchall()
            return [self._format_project(row) for row in rows]

    def get_all_events(self):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events")
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def add_project(self, name, curator, phone_number, email, description, tags=""):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO projects (name, curator, phone_number, email, description, tags)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (name, curator, phone_number, email, description, tags))
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                raise e

    def add_event(self, name, curator, phone_number, email, description, tags=""):
        self.add_project(name, curator, phone_number, email, description, tags)

    def add_event_detail(self, project_id, event_date, start_time, participants_count, participation_points, creator,
                         tags=""):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO events (project_id, event_date, start_time, participants_count, participation_points, creator, tags)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (project_id, event_date, start_time, participants_count, participation_points, creator, tags))
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                raise e

    def add_city(self, project_id, event_id, address, district, city, province, region, responsible_institution):
        with self.connect() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute('''
                    INSERT INTO cities (project_id, event_id, address, district, city, province, region, responsible_institution)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (project_id, event_id, address, district, city, province, region, responsible_institution))
                conn.commit()
            except sqlite3.IntegrityError as e:
                conn.rollback()
                raise e

    def get_user(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                return {
                    "id": user[0],
                    "first_name": user[1],
                    "last_name": user[2],
                    "email": user[3],
                    "registered_events": user[4],
                    "score": user[5],
                    "used_codes": user[6],
                    "tags": user[7],
                    "role": user[8]
                }
            return None

    def save_user(self, user_id, first_name, last_name, email, registered_events, score, used_codes, role, tags=""):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO users 
                (id, first_name, last_name, email, registered_events, score, used_codes, tags, role)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, first_name, last_name, email, registered_events, score, used_codes, tags, role))
            conn.commit()

    def update_user_role(self, user_id, new_role):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE users SET role = ? WHERE id = ?', (new_role, user_id))
            conn.commit()

    def delete_user(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            conn.commit()

    def find_user_by_id(self, user_id):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
            user = cursor.fetchone()
            if user:
                return {
                    "id": user[0],
                    "first_name": user[1],
                    "last_name": user[2],
                    "email": user[3],
                    "registered_events": user[4],
                    "score": user[5],
                    "used_codes": user[6],
                    "tags": user[7],
                    "role": user[8]
                }
            return None

    def find_users_by_name(self, name):
        pattern = f"%{name}%"
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE first_name LIKE ? OR last_name LIKE ?', (pattern, pattern))
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "first_name": row[1],
                    "last_name": row[2],
                    "email": row[3],
                    "registered_events": row[4],
                    "score": row[5],
                    "used_codes": row[6],
                    "tags": row[7],
                    "role": row[8]
                }
                for row in rows
            ]

    def find_users_by_email(self, email):
        pattern = f"%{email}%"
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM users WHERE email LIKE ?', (pattern,))
            rows = cursor.fetchall()
            return [
                {
                    "id": row[0],
                    "first_name": row[1],
                    "last_name": row[2],
                    "email": row[3],
                    "registered_events": row[4],
                    "score": row[5],
                    "used_codes": row[6],
                    "tags": row[7],
                    "role": row[8]
                }
                for row in rows
            ]

    def search_projects_by_tag(self, tag):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE tags LIKE ? LIMIT 5", (f"%{tag}%",))
            rows = cursor.fetchall()
            return [self._format_project(row) for row in rows]

    def search_projects_by_name(self, name):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE name LIKE ? LIMIT 5", (f"%{name}%",))
            rows = cursor.fetchall()
            return [self._format_project(row) for row in rows]

    def search_events_by_tag(self, tag):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events WHERE tags LIKE ? LIMIT 5", (f"%{tag}%",))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]

    def search_events_by_project_name(self, project_name):
        with self.connect() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT e.* FROM events e
                JOIN projects p ON e.project_id = p.id
                WHERE p.name LIKE ? LIMIT 5
            ''', (f"%{project_name}%",))
            rows = cursor.fetchall()
            return [self._format_event(row) for row in rows]
