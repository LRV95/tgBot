import sqlite3

from database.connection import get_db_connection

class ProjectModel:
    def get_project_by_name(self, name: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE name = ?", (name,))
        project = cursor.fetchone()
        conn.close()
        return project

    def get_project_by_id(self, project_id: int):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        conn.close()
        return project

    def add_project(self, name: str, description: str, responsible: str):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO projects (name, description, responsible) VALUES (?, ?, ?)", (name, description, responsible))
        conn.commit()
        conn.close()

    def get_all_projects(self):
        conn = get_db_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM projects")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]