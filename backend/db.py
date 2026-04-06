import psycopg2

conn = psycopg2.connect(
    dbname="eventsdb",
    user="myuser",
    password="mypass",
    host="localhost",  # connect to Docker Postgres from local
    port=5432,
)
cursor = conn.cursor()


def create_table():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS equipment_events (
            id SERIAL PRIMARY KEY,
            frame_id INT,
            equipment_id INT,
            equipment_type TEXT,
            timestamp TIMESTAMP,
            state TEXT,
            activity TEXT,
            motion_source TEXT
        )
        """
    )
    conn.commit()


def insert_event(event: dict):
    cursor.execute(
        """
        INSERT INTO equipment_events
        (frame_id, equipment_id, equipment_type, timestamp, state, activity, motion_source)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            event["frame_id"],
            event["equipment_id"],
            event["equipment_type"],
            event["timestamp"],
            event["state"],
            event["activity"],
            event["motion_source"],
        ),
    )
    conn.commit()


create_table()
