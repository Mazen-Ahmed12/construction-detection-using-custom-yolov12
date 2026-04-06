import psycopg2

conn = psycopg2.connect(
    dbname="eventsdb",
    user="myuser",
    password="mypass",
    host="localhost",
    port=5432,
)
cursor = conn.cursor()


def create_table():
    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS equipment_events (
            id SERIAL PRIMARY KEY,
            equipment_id INT,
            equipment_type TEXT,
            timestamp TIMESTAMP,
            state TEXT,
            activity TEXT,
            working_time FLOAT,
            idle_time FLOAT,
            utilization FLOAT
        )
        """
    )
    conn.commit()


def insert_event(event):
    cursor.execute(
        """
        INSERT INTO equipment_events
        (equipment_id, equipment_type, timestamp, state, activity,
         working_time, idle_time, utilization)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """,
        (
            event["equipment_id"],
            event["equipment_type"],
            event["timestamp"],
            event["state"],
            event["activity"],
            event["working_time"],
            event["idle_time"],
            event["utilization"],
        ),
    )
    conn.commit()


create_table()
