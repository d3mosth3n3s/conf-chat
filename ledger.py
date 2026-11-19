import json
import os
import threading
import uuid
from pathlib import Path


class MovieLedger:
    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.events = {}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding="utf-8"))
                for event in data:
                    if self.valid(event):
                        self.events[event["id"]] = event
            except (OSError, ValueError, TypeError):
                raise ValueError(f"Cannot read ledger file: {self.path}")

    @staticmethod
    def valid(event):
        return (
            isinstance(event, dict)
            and all(
                isinstance(event.get(k), str) and event[k].strip()
                for k in ("id", "user", "title")
            )
            and isinstance(event.get("year"), int)
            and not isinstance(event["year"], bool)
            and 1888 <= event["year"] <= 2200
            and len(event["id"]) <= 100
            and len(event["user"]) <= 80
            and len(event["title"]) <= 200
        )

    @staticmethod
    def movie_key(event):
        return (event["title"].strip().casefold(), event["year"])

    def _save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_name(self.path.name + ".tmp")
        tmp.write_text(
            json.dumps(list(self.events.values()), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        os.replace(tmp, self.path)

    def add(self, event):
        """Return True only if the event adds a new unique user/movie vote."""
        if not self.valid(event):
            return False
        with self.lock:
            if event["id"] in self.events:
                return False
            key = self.movie_key(event)
            if any(
                e["user"].casefold() == event["user"].casefold()
                and self.movie_key(e) == key
                for e in self.events.values()
            ):
                return False
            self.events[event["id"]] = event
            self._save()
            return True

    def recommend(self, user, title, year):
        event = {
            "id": str(uuid.uuid4()),
            "user": user,
            "title": title.strip(),
            "year": year,
        }
        return event if self.add(event) else None

    def snapshot(self):
        with self.lock:
            return list(self.events.values())

    def rankings(self):
        with self.lock:
            movies = {}
            for event in self.events.values():
                key = self.movie_key(event)
                if key not in movies:
                    movies[key] = {
                        "title": event["title"],
                        "year": event["year"],
                        "points": 0,
                    }
                movies[key]["points"] += 1
            return sorted(
                movies.values(),
                key=lambda x: (-x["points"], x["title"].casefold(), x["year"]),
            )
