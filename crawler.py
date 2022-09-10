#!/usr/bin/env python3
import re
import sys
import time

from lxml.html import fromstring
import requests
import sqlite3
import requests_cache
from requests_cache.backends.sqlite import DbCache

genre_uri_template = "https://www.netflix.com/browse/genre/%d"
xp_genre_title = "//div[@class='nm-collections-metadata-title']"
xp_genre_synopsis = "//div[@class='nm-collections-metadata-synopsis']"
xp_content_row = "//div[@class='nm-content-horizontal-row']/ul"
xp_row_item = "li[@class='nm-content-horizontal-row-item']"
xp_item_link = "a[contains(@class,'nm-collections-link')]/@href"
xp_item_title = "a/span[@class='nm-collections-title-name']"
xp_item_img = "a/img[@class='nm-collections-title-img']/@src"

AGED_REFRESH = 365.25 / 12 * 86400
rx_title_id = re.compile(r".+/(\d+)")

headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:104.0) Gecko/20100101 Firefox/104.0"}
session = requests.Session()
session.headers.update(headers)


def create_db(pathname):
    conn = sqlite3.connect(pathname)
    res = conn.execute("""
        CREATE TABLE IF NOT EXISTS genre (
            id INT PRIMARY KEY,
            name VARCHAR(128),
            synopsis VARCHAR(255),
            created DATETIME,
            updated DATETIME) """)

    res2 = conn.execute("""
        CREATE TABLE IF NOT EXISTS genre_history (
            id INT PRIMARY KEY,
            status INT,
            last DATETIME) """)

    res3 = conn.execute("""
        CREATE TABLE IF NOT EXISTS title (
            id INT PRIMARY KEY,
            name VARCHAR(128),
            img_src VARCHAR(255),
            last DATETIME) """)

    res4 = conn.execute("""
        CREATE TABLE IF NOT EXISTS genre_title (
            genre_id INT,
            title_id INT,
            last DATETIME,
            PRIMARY KEY(genre_id, title_id)) """)

    return conn


def main(start_nr: int = 0):
    db = create_db("./netflix_genres.sqlite3")

    # https://requests-cache.readthedocs.io/
    sqlite_cache = DbCache(db_path="./requests_cache.sqlite")
    requests_cache.install_cache(
        cache_name="http_cache",
        backend=sqlite_cache,
        expire_after=-1,  # never expire
        allowable_codes=(200, 301, 404),  # cache responses for these codes
    )

    for genre_id in range(start_nr, int(1e6)):
        title_insert_buffer = []
        title_genre_insert_buffer = []

        uri = genre_uri_template % genre_id

        request_start = time.time()
        response = requests.get(uri, headers=headers)
        request_end = now = time.time()
        print(f"{request_end-request_start:2.6f} - {uri}")

        db.execute(
            f"""INSERT INTO genre_history
                (id, status, last)
                VALUES(?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET 
                    status=?,
                    last=?""",
            (genre_id, response.status_code, time.time(), response.status_code, time.time()))

        db.commit()

        if response.status_code != 200:
            continue

        page = fromstring(response.content)
        try:
            genre_name = page.xpath(xp_genre_title)[0].text_content().strip()
            synopsis = page.xpath(xp_genre_synopsis)[0].text_content().strip()
        except Exception as xxx:
            print(f"Skipping genre id: {genre_id}")
            continue

        genre_exists = db.execute(
            f"""SELECT * FROM genre
                WHERE id=?
                AND ? - updated > ?
                AND (name != ?
                     OR synopsis != ?) """,
            (genre_id, now, AGED_REFRESH, genre_name, synopsis))

        if genre_exists.rowcount < 0:
            db.execute(
                """INSERT INTO genre
                   (id, name, synopsis, created, updated)
                   VALUES(?, ?, ?, ?, ?)
                   ON CONFLICT(id) DO UPDATE SET
                       name=?,
                       synopsis=?,
                       updated=? """, (genre_id, genre_name, synopsis, now, now, genre_name, synopsis, now))
            db.commit()

        found, skipped = 0, 0
        for ir, genre_row_titles in enumerate(page.xpath(xp_content_row)):
            for it, item in enumerate(genre_row_titles):
                try:
                    item_link = item.xpath(xp_item_link)[0].strip()
                    title_id = rx_title_id.match(item_link).groups(0)[0].strip()
                    item_title = item.xpath(xp_item_title)[0].text_content().strip()
                    item_img = item.xpath(xp_item_img)[0].strip()
                    title_insert_buffer.append((title_id, item_title, item_img, now, item_title, item_img, now))
                    title_genre_insert_buffer.append((genre_id, title_id, now, now))
                    found += 1
                except Exception as dd:
                    skipped += 1
        print(f"Found {found}, skipped partial items {skipped} on {genre_name} ({uri})")

        db.executemany(
            """INSERT INTO title
                (id, name, img_src, last)
                VALUES(?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    name=?,
                    img_src=?,
                    last=? """,
            title_insert_buffer)
        db.commit()

        db.executemany(
            """INSERT INTO genre_title
                (genre_id, title_id, last)
                VALUES(?, ?, ?)
                ON CONFLICT(genre_id, title_id) DO UPDATE SET
                    last=? """,
            title_genre_insert_buffer)

        db.commit()


if __name__ == '__main__':
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    main(start)
