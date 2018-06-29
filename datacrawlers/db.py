import sqlite3
import uuid
from datetime import datetime

conn = sqlite3.connect("vauva.db")


def create_tables():
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS comments (comment_id integer, parent_id text, comment text, reply text, unix int)''')
    c.execute('''CREATE TABLE IF NOT EXISTS pages (page text)''')

    conn.commit()


p_batch = 0
c_batch = 0


def insert_page(page):
    global p_batch
    c = conn.cursor()
    print("inserting page {}".format(page))
    c.execute("INSERT INTO pages VALUES (?)", (page,))
    p_batch = p_batch + 1
    if p_batch % 50 == 0:
        print("committing p_batch " + str(p_batch))
        conn.commit()


def insert_comments(comments):
    global c_batch
    c = conn.cursor()
    print("comments: {}".format(len(comments)))
    for comment in comments:
        if comment and comment.get('comment_id') != None:
            c.execute("INSERT INTO comments (comment_id, parent_id, comment, reply, unix) VALUES (?, ?, ?, ?, ?)",
                      (comment['comment_id'], comment['parent_id'], comment['comment'], comment['reply'], datetime.now()))
            c_batch += 1
            if c_batch % 50 == 0:
                print("committing c_batch " + str(c_batch))
                conn.commit()
            if c_batch % 500 == 0:
                print("total comments so far " + str(count_comments()))
    # print("committing rest of comments")
    # conn.commit()


def count_comments():
    c = conn.cursor()
    c.execute("select count(*) from comments")
    return c.fetchone()


def find_page(page_name):
    c = conn.cursor()
    c.execute("SELECT page from pages WHERE page=?", (page_name,))
    page = c.fetchone()
    if page:
        return True
    return False


def close():
    conn.commit()
    conn.close()
