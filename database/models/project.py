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
