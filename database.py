"""Local and optional cloud persistence for VeriQuest AI conversations."""

import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

import pymongo

from pipelines.dialogue_state import DialogueState
from utils.logging import logger

cosmos_db_client = None
dialogue_db_collection = None
preference_db_collection = None

LOCAL_DATA_DIR = Path(__file__).resolve().parent / "data"
LOCAL_DATABASE_PATH = LOCAL_DATA_DIR / "veriquest_ai.sqlite3"


def initialize_local_database() -> None:
    """Create the private, on-device chat archive if it does not exist."""
    LOCAL_DATA_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(LOCAL_DATABASE_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS conversations (
                dialogue_id TEXT PRIMARY KEY,
                chat_profile TEXT NOT NULL,
                started_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dialogue_id TEXT NOT NULL,
                turn_id INTEGER NOT NULL,
                user_utterance TEXT NOT NULL,
                agent_utterance TEXT NOT NULL,
                sources_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                UNIQUE(dialogue_id, turn_id),
                FOREIGN KEY(dialogue_id) REFERENCES conversations(dialogue_id)
            )
            """
        )


def save_turn_locally(
    dialogue_state: DialogueState, dialogue_id: str, chat_profile: str
) -> None:
    """Persist the latest completed turn to an SQLite file on this laptop."""
    if not dialogue_state.turns:
        return

    latest_turn = dialogue_state.current_turn
    if not latest_turn.user_utterance or not latest_turn.agent_utterance:
        return

    now = datetime.now(timezone.utc).isoformat()
    sources = [
        {
            "title": result.full_title,
            "url": result.url,
            "summary": result.summary,
        }
        for result in latest_turn.filtered_search_results
    ]
    try:
        initialize_local_database()
        with sqlite3.connect(LOCAL_DATABASE_PATH) as connection:
            connection.execute(
                """
                INSERT INTO conversations (dialogue_id, chat_profile, started_at, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(dialogue_id) DO UPDATE SET
                    chat_profile = excluded.chat_profile,
                    updated_at = excluded.updated_at
                """,
                (dialogue_id, chat_profile, now, now),
            )
            connection.execute(
                """
                INSERT INTO messages (
                    dialogue_id, turn_id, user_utterance, agent_utterance,
                    sources_json, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(dialogue_id, turn_id) DO UPDATE SET
                    user_utterance = excluded.user_utterance,
                    agent_utterance = excluded.agent_utterance,
                    sources_json = excluded.sources_json
                """,
                (
                    dialogue_id,
                    len(dialogue_state.turns) - 1,
                    latest_turn.user_utterance,
                    latest_turn.agent_utterance,
                    json.dumps(sources, ensure_ascii=False),
                    now,
                ),
            )
    except sqlite3.Error as exc:
        logger.error("Could not save local chat history: %s", exc)


def get_recent_local_chats(limit: int = 6) -> list[dict[str, str]]:
    """Return recent conversation previews for the welcome-screen chat cards."""
    if not LOCAL_DATABASE_PATH.exists():
        return []
    try:
        with sqlite3.connect(LOCAL_DATABASE_PATH) as connection:
            connection.row_factory = sqlite3.Row
            rows = connection.execute(
                """
                SELECT c.dialogue_id, c.updated_at, m.user_utterance
                FROM conversations AS c
                JOIN messages AS m
                    ON m.dialogue_id = c.dialogue_id AND m.turn_id = 0
                ORDER BY c.updated_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("Could not read local chat history: %s", exc)
        return []


def initialize_db_connection():
    logger.info("Initializing Cosmos DB connection")
    CONNECTION_STRING = os.environ.get("COSMOS_CONNECTION_STRING")
    if not CONNECTION_STRING:
        logger.warning(
            "COSMOS_CONNECTION_STRING is not set; conversation persistence is disabled."
        )
        return False

    global cosmos_db_client, dialogue_db_collection, preference_db_collection
    cosmos_db_client = pymongo.MongoClient(CONNECTION_STRING)
    db = cosmos_db_client["veriquest-ai"]  # the database name is veriquest-ai
    dialogue_db_collection = db[
        "dialog_turns"
    ]  # the collection that stores dialog turns and their user ratings
    dialogue_db_collection.create_index(
        "$**"
    )  # necessary to build an index before we can call sort()
    preference_db_collection = db[
        "preferences"
    ]  # the collection that stores information about what utterance users preferred
    preference_db_collection.create_index(
        "$**"
    )  # necessary to build an index before we can call sort()
    # The "schema" of dialogue_db_collection is: {_id=(dialog_id, turn_id, system_name), experiment_id, dialog_id, turn_id, system_name, user_utterance, agent_utterance, agent_log_object, user_naturalness_rating}
    # The "schema" of preference_db_collection is: {_id=(dialog_id, turn_id), experiment_id, dialog_id, turn_id, winner_system, loser_systems}
    return True


def save_dialogue_to_db(
    dialogue_state: DialogueState,
    dialogue_id: str,
    system_name: str,
    experiment_id: str = "default-experiment",
):
    if cosmos_db_client is None:
        if not initialize_db_connection():
            return
    entries_to_write = []
    for turn_id, dialogue_turn in enumerate(dialogue_state.turns):
        entries_to_write.append(
            {
                "_id": str((dialogue_id, turn_id, system_name)),
                "experiment_id": experiment_id,
                "dialog_id": dialogue_id,
                "turn_id": turn_id,
                "system_name": system_name,
                "user_utterance": dialogue_turn.user_utterance,
                "agent_utterance": dialogue_turn.agent_utterance,
                "agent_log_object": dialogue_turn.model_dump(),
            }
        )
    try:
        logger.info(f"Saving dialogue '{dialogue_id}' to database")
        dialogue_db_collection.insert_many(entries_to_write)
    except Exception as e:
        logger.error(f"Could not save '{dialogue_id}' to database: {e}")
