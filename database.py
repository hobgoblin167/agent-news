import sqlite3

DB_PATH = "news.db"


def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS news (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                external_id TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT,
                published_at TEXT,
                article_text TEXT,
                summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

    print("Database initialized successfully")


def get_existing_ids(ids: list[str]) -> set[str]:
    if not ids:
        return set()

    placeholders = ",".join(["?"] * len(ids))

    query = f"""
        SELECT external_id
        FROM news
        WHERE external_id IN ({placeholders})
    """

    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(query, ids).fetchall()

    return {row[0] for row in rows}


def save_articles(articles: list[dict]):
    with sqlite3.connect(DB_PATH) as conn:
        for article in articles:
            conn.execute("""
                INSERT OR IGNORE INTO news (
                    external_id,
                    title,
                    url,
                    source,
                    published_at,
                    article_text,
                    summary
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                article["id"],
                article["title"],
                article["url"],
                article.get("source"),
                article.get("published_at"),
                article.get("text"),
                article.get("summary")
            ))

        conn.commit()


def show_all_news():
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT id, title, source, created_at
            FROM news
            ORDER BY created_at DESC
        """).fetchall()

    for row in rows:
        print("-" * 80)
        print("ID:", row[0])
        print("Title:", row[1])
        print("Source:", row[2])
        print("Created:", row[3])