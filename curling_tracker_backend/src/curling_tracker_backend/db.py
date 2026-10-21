import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator, List, Union, Tuple
from flask import Flask, current_app, g
import numpy as np
import io
import logging

logger = logging.getLogger(__name__)

# How long to wait for another connection (e.g. the tracking worker) to release a lock
DB_TIMEOUT_SECONDS = 30

# Columns added to tables after they were first created, as (table, column, type). CREATE TABLE IF NOT
# EXISTS doesn't add them to an existing database, so init_db does.
ADDED_COLUMNS = [
    ("TrackingRuns", "video_title", "TEXT"),
    ("TrackingRuns", "video_date", "TEXT"),
    ("TrackingRuns", "video_start_timestamp", "REAL"),
    ("Shots", "back_line_to_hog_seconds", "REAL"),
    ("Shots", "hog_to_hog_seconds", "REAL"),
]


def adapt_matrix(arr: np.ndarray) -> sqlite3.Binary:
    """Converts a numpy array into binary for storing in a database

    Args:
        arr (np.ndarray): The array to convert

    Returns:
        sqlite3.Binary: The binary for the array
    """
    out = io.BytesIO()
    np.save(out, arr, allow_pickle=False)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_matrix(text: str):
    """Convert binary back into a numpy array

    Args:
        text (str): The binary to convert

    Returns:
        np.ndarray: The output numpy array.
    """
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out, allow_pickle=False)


def get_db(db_name="primary") -> sqlite3.Connection:
    """Connect to the database

    Returns:
        sqlite3.Connection: The connection to the database
    """

    if db_name == "primary":
        logger.debug(
            f"Connecting to database... {current_app.config['DATABASE']}")
        db = sqlite3.connect(current_app.config["DATABASE"],
                             detect_types=sqlite3.PARSE_DECLTYPES,
                             timeout=DB_TIMEOUT_SECONDS)
    elif db_name == "datasets":
        logger.debug(
            f"Connecting to database... {current_app.config['DATASETS_DATABASE']}"
        )
        db = sqlite3.connect(current_app.config["DATASETS_DATABASE"],
                             detect_types=sqlite3.PARSE_DECLTYPES,
                             timeout=DB_TIMEOUT_SECONDS)
    db.row_factory = sqlite3.Row
    return db


def query_db(query: str,
             args=(),
             one: bool = False,
             db_name="primary") -> Union[sqlite3.Row, List[sqlite3.Row]]:
    """Query the database, commit to the database, and get the results back

    Args:   
        query (str): The query to use
        args (Tuple[Any], optional): The args for that query. Defaults to ().
        one (bool, optional): If True only return the first row, otherwise return all rows. Defaults to False.

    Returns:
        Union[sqlite3.Row, List[sqlite3.Row]]: The rows containing the results of the query
    """
    conn = get_db(db_name)
    cur = conn.execute(query, args)
    conn.commit()
    rv = cur.fetchall()
    cur.close()

    conn.close()

    return (rv[0] if rv else None) if one else rv


@contextmanager
def db_transaction(db_name="primary") -> Iterator[sqlite3.Connection]:
    """Run several statements on one connection as a single transaction.
    Commits when the block exits normally and rolls back if it raises.

    Yields:
        sqlite3.Connection: The connection to execute statements on
    """
    conn = get_db(db_name)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Initialize the database using the schemas.sql script"""
    db = get_db()

    # Lets the API read while the tracking worker writes
    db.execute("PRAGMA journal_mode=WAL")

    with current_app.open_resource("schemas.sql") as f:
        db.executescript(f.read().decode("utf8"))

    for table, column, column_type in ADDED_COLUMNS:
        existing = [row[1] for row in db.execute(f"PRAGMA table_info({table})")]
        if column not in existing:
            logger.info(f"Adding column {column} to {table}")
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")
    db.commit()

    db.close()


def clear_db():
    """Clear the database using the clear.sql script and reinitalize with schemas.sql"""
    db = get_db()

    with current_app.open_resource("clear.sql") as f:
        db.executescript(f.read().decode("utf8"))

    with current_app.open_resource("schemas.sql") as f:
        db.executescript(f.read().decode("utf8"))

    db.close()


def init_app(app: Flask):
    """Initialize the app to use the database.

    Args:
        app (Flask): The flask app to initalize.
    """
    sqlite3.register_adapter(np.ndarray, adapt_matrix)
    sqlite3.register_converter("matrix", convert_matrix)
