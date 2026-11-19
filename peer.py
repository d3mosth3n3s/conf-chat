import json
import socket
import threading
import uuid
from datetime import datetime
from ledger import MovieLedger


class Peer:
    def __init__(self, name, host, port, display, ledger_path=None):
        self.name, self.host, self.port = name, host, port
        self.display = display
        self.node_id = str(uuid.uuid4())
        self.ledger = MovieLedger(ledger_path or f"ledger_{name}_{port}.json")
        self.connections = {}
        self.seen = set()
        self.rooms = {}
        self.current_room = None
        self.lock = threading.RLock()
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((host, port))
        self.server.listen()
        threading.Thread(target=self._accept, daemon=True).start()

    def _send(self, sock, message):
        try:
            sock.sendall((json.dumps(message) + "\n").encode("utf-8"))
            return True
        except OSError:
            self._remove(sock)
            return False

    def _hello(self):
        return {
            "type": "HELLO",
            "id": self.node_id,
            "name": self.name,
            "host": self.host,
            "port": self.port,
        }

    def _accept(self):
        while self.running:
            try:
                sock, _ = self.server.accept()
            except OSError:
                break
            self._register(sock)

    def _register(self, sock):
        with self.lock:
            self.connections[sock] = None
        threading.Thread(target=self._read, args=(sock,), daemon=True).start()
        self._send(sock, self._hello())

    def connect(self, host, port):
        if port == self.port and host in (self.host, "127.0.0.1", "localhost"):
            return
        with self.lock:
            if any(
                info and info["host"] == host and info["port"] == port
                for info in self.connections.values()
            ):
                return
        try:
            sock = socket.create_connection((host, port), timeout=3)
            sock.settimeout(None)
            self._register(sock)
        except OSError as exc:
            self.display(f"Could not connect to {host}:{port}: {exc}")

    def _remove(self, sock):
        with self.lock:
            info = self.connections.pop(sock, None)
        try:
            sock.close()
        except OSError:
            pass
        if info:
            self.display(f"[Disconnected: {info['name']}]")

    def _read(self, sock):
        try:
            with sock.makefile("r", encoding="utf-8") as stream:
                for line in stream:
                    try:
                        msg = json.loads(line)
                        if isinstance(msg, dict):
                            self._handle(sock, msg)
                    except (ValueError, KeyError, TypeError):
                        continue
        except (OSError, UnicodeError):
            pass
        finally:
            self._remove(sock)

    def _handle(self, sock, msg):
        kind = msg.get("type")
        if kind == "HELLO":
            if not isinstance(msg.get("port"), int) or not isinstance(
                msg.get("name"), str
            ):
                return
            if msg.get("id") == self.node_id:
                self._remove(sock)
                return
            info = {key: msg[key] for key in ("id", "name", "host", "port")}
            with self.lock:
                self.connections[sock] = info
                peers = [p for p in self.connections.values() if p]
            self.display(f"[Connected: {info['name']}]")
            self._send(sock, {"type": "PEERS", "peers": peers})
            self._send(sock, {"type": "LEDGER_SYNC", "events": self.ledger.snapshot()})
            with self.lock:
                room_names = list(self.rooms.values())
            self._send(sock, {"type": "ROOM_SYNC", "rooms": room_names})
        elif kind == "PEERS":
            for p in msg.get("peers", [])[:100]:
                if not isinstance(p, dict):
                    continue
                if not isinstance(p.get("port"), int) or not isinstance(
                    p.get("host"), str
                ):
                    continue
                if p.get("id") == self.node_id:
                    continue
                with self.lock:
                    already = any(
                        i and i.get("id") == p.get("id")
                        for i in self.connections.values()
                    )
                if not already and self.node_id < str(p.get("id", "")):
                    threading.Thread(
                        target=self.connect, args=(p["host"], p["port"]), daemon=True
                    ).start()
        elif kind == "LEDGER_SYNC":
            events = msg.get("events")
            if not isinstance(events, list):
                return
            for event in events[:10000]:
                if self.ledger.add(event):
                    self.display(
                        f"[Movie] {event['user']} recommended {event['title']} ({event['year']})"
                    )
                    self._broadcast({"type": "MOVIE", "event": event}, exclude=sock)
        elif kind == "MOVIE":
            event = msg.get("event")
            if self.ledger.add(event):
                self.display(
                    f"[Movie] {event['user']} recommended {event['title']} ({event['year']})"
                )
                self._broadcast(msg, exclude=sock)
        elif kind == "ROOM_SYNC":
            rooms = msg.get("rooms")
            if isinstance(rooms, list):
                for name in rooms[:500]:
                    self._register_room(name, exclude=sock)
        elif kind == "ROOM_CREATE":
            self._register_room(msg.get("room"), exclude=sock)
        elif kind in ("GROUP", "PRIVATE", "ROOM_CHAT"):

            message_id = msg.get("id")
            if not isinstance(message_id, str) or not isinstance(msg.get("text"), str):
                return
            with self.lock:
                if message_id in self.seen:
                    return
                self.seen.add(message_id)
                if len(self.seen) > 10000:
                    self.seen.clear()
            if kind == "GROUP":
                self.display(f"[Group] {msg.get('from', '?')}: {msg['text']}")
            elif kind == "ROOM_CHAT":
                room = msg.get("room")
                if isinstance(room, str) and self.current_room == room.casefold():
                    self.display(f"[{room}] {msg.get('from', '?')}: {msg['text']}")
            elif msg.get("to") == self.name:
                self.display(f"[Private] {msg.get('from', '?')}: {msg['text']}")
            self._broadcast(msg, exclude=sock)

    def _broadcast(self, msg, exclude=None):
        with self.lock:
            sockets = list(self.connections)
        for sock in sockets:
            if sock is not exclude:
                self._send(sock, msg)

    def send_message(self, text, recipient=None):
        msg = {
            "type": "PRIVATE" if recipient else "GROUP",
            "id": str(uuid.uuid4()),
            "from": self.name,
            "text": text,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        if recipient:
            msg["to"] = recipient
        with self.lock:
            self.seen.add(msg["id"])
        self._broadcast(msg)

    def _register_room(self, name, exclude=None):
        if not isinstance(name, str):
            return False
        name = name.strip()
        if not 1 <= len(name) <= 80:
            return False
        key = name.casefold()
        with self.lock:
            if key in self.rooms:
                return False
            self.rooms[key] = name
        self._broadcast({"type": "ROOM_CREATE", "room": name}, exclude=exclude)
        return True

    def create_room(self, name):
        if self._register_room(name):
            self.current_room = name.strip().casefold()
            return True
        return False

    def join_room(self, name):
        key = name.strip().casefold()
        with self.lock:
            if key not in self.rooms:
                return False
        self.current_room = key
        return True

    def leave_room(self):
        self.current_room = None

    def list_rooms(self):
        with self.lock:
            return sorted(self.rooms.values(), key=str.casefold)

    def room_message(self, text):
        with self.lock:
            room = self.rooms.get(self.current_room)
        if not room or not text.strip():
            return False
        msg = {
            "type": "ROOM_CHAT",
            "id": str(uuid.uuid4()),
            "from": self.name,
            "room": room,
            "text": text,
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        }
        with self.lock:
            self.seen.add(msg["id"])
        self._broadcast(msg)
        return True

    def recommend_movie(self, title, year):
        event = self.ledger.recommend(self.name, title, year)
        if event:
            self._broadcast({"type": "MOVIE", "event": event})
        return event is not None

    def movie_rankings(self):
        return self.ledger.rankings()

    def peers(self):
        with self.lock:
            return [p["name"] for p in self.connections.values() if p]

    def close(self):
        self.running = False
        self.server.close()
        with self.lock:
            sockets = list(self.connections)
        for sock in sockets:
            self._remove(sock)
