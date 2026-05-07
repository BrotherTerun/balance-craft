import os
import mysql.connector

DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '2256'
}

DATABASE_NAME = "monitor_rpg_model"


def execute_sql_file(cursor, filepath):

    print(f"[DB] Выполнение: {filepath}")

    with open(filepath, "r", encoding="utf-8") as file:
        sql_script = file.read()

    commands = sql_script.split(";")

    for command in commands:

        command = command.strip()

        if command:
            cursor.execute(command)


def initialize_database():

    base_dir = os.path.dirname(
        os.path.abspath(__file__)
    )

    project_root = os.path.abspath(
        os.path.join(base_dir, "..", "..")
    )

    sql_dir = os.path.join(
        project_root,
        "Database",
        "SQL_Scripts"
    )

    create_tables_path = os.path.join(
        sql_dir,
        "Create_Tables.sql"
    )

    csv_fill_path = os.path.join(
        sql_dir,
        "CSV_fill_script.sql"
    )

    print("[DB] Подключение к MySQL...")

    conn = mysql.connector.connect(
        host='localhost',
        user='root',
        password='2256',
        allow_local_infile=True
    )

    cursor = conn.cursor()

    print("[DB] Создание БД...")

    cursor.execute(
        f"CREATE DATABASE IF NOT EXISTS {DATABASE_NAME}"
    )

    conn.database = DATABASE_NAME

    print("[DB] Создание таблиц...")

    execute_sql_file(
        cursor,
        create_tables_path
    )

    print("[DB] Заполнение seed-данных...")

    execute_sql_file(
        cursor,
        csv_fill_path
    )

    conn.commit()

    cursor.close()
    conn.close()

    print("[DB] Инициализация завершена")