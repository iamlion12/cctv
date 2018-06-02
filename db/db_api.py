import os
import sqlite3
import imageio
import numpy as np

create_files_table = """
                        CREATE TABLE IF NOT EXISTS files(
                        id integer PRIMARY KEY,
                        name text NOT NULL);
                     """

create_warning_time_table = """
                                CREATE TABLE IF NOT EXISTS warning_time(
                                id integer PRIMARY KEY,
                                time_start text NOT NULL,
                                end_time text NOT NULL,
                                file_id integer NOT NULL,
                                FOREIGN KEY (file_id) REFERENCES files (id));
                            """

create_warning_images_table = """
                                 CREATE TABLE IF NOT EXISTS warning_images(
                                 id integer PRIMARY KEY,
                                 time integer NOT NULL,
                                 image text NOT NULL,
                                 FOREIGN KEY (time) REFERENCES warning_time (id));
                              """

def create_connection(db_file):
    try:
        con = sqlite3.connect(db_file)
        print("Successfully connected to database.")
        return con

    except sqlite3.Error as e:
        return None

    return None

def create_table(con, sql_expession):
    try:
        c = con.cursor()
        c.execute(sql_expession)

    except sqlite3.Error as e:
        print(e)

def add_file(con, values):

    sql = "INSERT INTO files(name) VALUES(?);"
    c = con.cursor()
    c.execute(sql, (values,))
    print("Done.")

    return c.lastrowid

def add_time(con, values):

    sql = "INSERT INTO warning_time(time_start, end_time, file_id) VALUES(?, ?, ?);"
    c = con.cursor()
    c.execute(sql, values)

    return c.lastrowid

def add_image(con, values):

    sql = "INSERT INTO warning_images(time, image) VALUES(?, ?);"
    c = con.cursor()
    c.execute(sql, values)

    return c.lastrowid

def delete_images(con):
    sql = """DELETE FROM warning_images WHERE id>=0"""
    c = con.cursor()
    c.execute(sql)

    return c.lastrowid

def select_file(con, name):
    c = con.cursor()
    c.execute("SELECT id FROM files where name = ?", (name,))

    rows = c.fetchall()
    if rows:
        return rows[0][0]
    else: return None

def select_time(con, id):
    c = con.cursor()
    c.execute("SELECT time_start, end_time FROM warning_time WHERE file_id = ?", (id,))

    rows = c.fetchall()

    return rows

def select_images(con, time):
    c = con.cursor()
    c.execute("SELECT image FROM warning_images WHERE time = ?", (time,))

    rows = c.fetchall()

    return rows

def main():

    con = create_connection(os.path.join(os.getcwd(), 'data.db'))

    if con is not None:
        create_table(con, create_files_table)
        create_table(con, create_warning_time_table)
        create_table(con, create_warning_images_table)
    else:
        print("Cannot connect to database.")

    print(con)

    try:
        with con:
            pass

    except Exception as e:
        print("Error", e)

if __name__ == "__main__":
    main()
