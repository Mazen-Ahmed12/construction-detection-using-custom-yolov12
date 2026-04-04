import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)  # add project root

from fastapi import FastAPI
from db.db import cursor

app = FastAPI()


@app.get("/events")
def get_events(limit: int = 100):

    cursor.execute("SELECT * FROM equipment_events ORDER BY id DESC LIMIT %s", (limit,))
    rows = cursor.fetchall()
    result = []
    for row in rows:
        result.append(
            {
                "id": row[0],
                "frame_id": row[1],
                "equipment_id": row[2],
                "equipment_type": row[3],
                "timestamp": row[4].isoformat(),
                "state": row[5],
                "activity": row[6],
                "motion_source": row[7],
            }
        )
    return result
