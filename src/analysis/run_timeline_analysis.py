import os
import re
from pathlib import Path
from dotenv import load_dotenv, find_dotenv

import psycopg

load_dotenv(find_dotenv(usecwd=True))

DB_CONFIG = {
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", 5432)),
}

SQL_PATH = Path(__file__).parent.parent.parent / "sql/timeline_analysis.sql"

QUERY_MARKER = re.compile(r"^-- QUERY: (\w+)\n", re.MULTILINE)


def load_queries(path: Path) -> list[tuple[str, str]]:
    content = path.read_text(encoding="utf-8")

    sections = QUERY_MARKER.split(content)

    queries = []
    for index in range(1, len(sections), 2):
        name = sections[index]
        sql = sections[index + 1].strip()
        queries.append((name, sql))

    return queries


def format_rows(columns: list[str], rows: list[tuple]) -> str:
    widths = [
        max(len(str(column)), *(len(str(value)) for value in row))
        for column, row in zip(columns, zip(*rows))
    ]

    def render(values):
        return "  ".join(
            str(value).rjust(width) for value, width in zip(values, widths)
        )

    lines = [render(columns)]
    lines.append("  ".join("-" * width for width in widths))
    lines.extend(render(row) for row in rows)

    return "\n".join(lines)


def main():
    queries = load_queries(SQL_PATH)

    with psycopg.connect(**DB_CONFIG) as connection:
        with connection.cursor() as cursor:
            for name, sql in queries:
                cursor.execute(sql)
                columns = [description.name for description in cursor.description]
                rows = cursor.fetchall()

                print(f"\n=== {name} ===")
                if not rows:
                    print("no results")
                    continue
                print(format_rows(columns, rows))


if __name__ == "__main__":
    main()