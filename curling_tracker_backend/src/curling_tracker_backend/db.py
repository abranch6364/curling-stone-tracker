import os
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
        if current_app.config.get("READ_ONLY", False):
            # Read only, so a published database can't be changed by the server
            db = sqlite3.connect(
                f"file:{current_app.config['DATABASE']}?mode=ro",
                uri=True,
                detect_types=sqlite3.PARSE_DECLTYPES,
                timeout=DB_TIMEOUT_SECONDS)
        else:
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

    db.commit()

    db.close()


def publish_db(output_path: str, completed_runs_only: bool = True) -> dict:
    """Write a copy of the database for a read only server.

    The copy is a single file, not in WAL mode, since a read only connection can't create the WAL files. It's
    written next to output_path and then renamed, so a server reading output_path never sees it half written.

    Args:
        output_path (str): Where to write the copy
        completed_runs_only (bool, optional): Leave out the runs that didn't complete (failed, cancelled or
            still being processed), with their draws. Defaults to True.

    Returns:
        dict: The number of runs, draws and shots in the copy, and its size in bytes
    """
    temp_path = output_path + ".tmp"
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # A consistent snapshot, even while the tracking worker is writing
    source = get_db()
    source.execute("VACUUM INTO ?", [temp_path])
    source.close()

    copy = sqlite3.connect(temp_path)
    copy.execute("PRAGMA journal_mode=DELETE")
    if completed_runs_only:
        unfinished_games = """SELECT Games.game_id FROM Games JOIN TrackingRuns ON Games.run_id = TrackingRuns.run_id
                              WHERE TrackingRuns.status != 'complete'"""
        unfinished_ends = f"SELECT end_id FROM Ends WHERE game_id IN ({unfinished_games})"
        unfinished_shots = f"SELECT shot_id FROM Shots WHERE end_id IN ({unfinished_ends})"
        copy.execute(f"DELETE FROM ShotStones WHERE shot_id IN ({unfinished_shots})")
        copy.execute(f"DELETE FROM Shots WHERE shot_id IN ({unfinished_shots})")
        copy.execute(f"DELETE FROM Ends WHERE end_id IN ({unfinished_ends})")
        copy.execute(f"DELETE FROM Games WHERE game_id IN ({unfinished_games})")
        copy.execute("DELETE FROM TrackingRuns WHERE status != 'complete'")
        copy.commit()
        # Shrinks the file after the deletes
        copy.execute("VACUUM")

    summary = {
        "runs": copy.execute("SELECT COUNT(*) FROM TrackingRuns").fetchone()[0],
        "draws": copy.execute("SELECT COUNT(*) FROM Games").fetchone()[0],
        "shots": copy.execute("SELECT COUNT(*) FROM Shots").fetchone()[0],
    }
    copy.close()

    os.chmod(temp_path, 0o644)
    os.replace(temp_path, output_path)
    summary["bytes"] = os.path.getsize(output_path)
    return summary


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
