import argparse
from peer import Peer


def main():
    parser = argparse.ArgumentParser(description="Decentralized P2P chat")
    parser.add_argument("--name", required=True, help="Your unique username")
    parser.add_argument("--port", required=True, type=int, help="Port to listen on")
    parser.add_argument("--host", default="127.0.0.1", help="Reachable IP address")
    parser.add_argument("--connect", help="IP of an existing peer")
    parser.add_argument("--peer-port", type=int, help="Port of an existing peer")
    args = parser.parse_args()
    peer = Peer(args.name, args.host, args.port, print)
    if args.connect and args.peer_port:
        peer.connect(args.connect, args.peer_port)
    print("--BETTERBOXD--")
    print("A P2P Movie Chatroom")
    print("-------------------------")
    print("  /all MESSAGE           Send a group message")
    print("  /msg USER MESSAGE      Send a private message")
    print("  /connect HOST PORT     Connect to another peer")
    print("  /peers                 Show directly connected peers")
    print("  /movie TITLE | YEAR    Recommend a movie (one vote per user/movie)")
    print("  /movies                Show movie rankings")
    print("  /create MOVIE          Create and join a movie discussion room")
    print("  /rooms                 List movie discussion rooms")
    print("  /whereami              Show your current location in the chat")
    print("  /join MOVIE            Join an existing room")
    print("  /say MESSAGE           Send a message to your current room")
    print("  /leave                 Leave your current room")
    print("  /quit                  Exit")
    print("-------------------------")
    try:
        while True:
            line = input("> ").strip()
            if line == "/quit":
                break
            elif line == "/peers":
                print("Connected:", ", ".join(peer.peers()) or "(none)")
            elif line == "/whereami":
                print(f"Username: {peer.name}")
                print(f"Address: {peer.host}:{peer.port}")

                if peer.current_room is None:
                    print("Current room: General chat")
                else:
                    room_name = peer.rooms.get(peer.current_room)
                    print(f"Current room: {room_name}")
            elif line.startswith("/all "):
                peer.send_message(line[5:])
                print(f"[Group] You: {line[5:]}")
            elif line.startswith("/msg "):
                parts = line.split(" ", 2)
                if len(parts) == 3:
                    peer.send_message(parts[2], parts[1])
                    print(f"[Private to {parts[1]}] You: {parts[2]}")
                else:
                    print("Usage: /msg USER MESSAGE")
            elif line == "/rooms":
                rooms = peer.list_rooms()
                print("Rooms:", ", ".join(rooms) if rooms else "(none)")
            elif line.startswith("/create "):
                name = line[8:].strip()
                if peer.create_room(name):
                    print(f"[Room] Created and joined {name}")
                else:
                    print("Invalid name or room already exists. Use /join to enter it.")
            elif line.startswith("/join "):
                name = line[6:].strip()
                if peer.join_room(name):
                    print(f"[Room] Joined {name}")
                else:
                    print("Room not found. Use /rooms to see available rooms.")
            elif line == "/leave":
                peer.leave_room()
                print("[Room] Left the current room.")
            elif line.startswith("/say "):
                if peer.room_message(line[5:]):
                    print(f"[Room] You: {line[5:]}")
                else:
                    print("Join a room first using /join MOVIE.")
            elif line == "/movies":
                rankings = peer.movie_rankings()
                if not rankings:
                    print("No movie recommendations yet.")
                for i, movie in enumerate(rankings, 1):
                    print(
                        f"{i}. {movie['title']} ({movie['year']}) - {movie['points']} point(s)"
                    )
            elif line.startswith("/movie "):
                try:
                    title, year_text = line[7:].rsplit("|", 1)
                    title, year = title.strip(), int(year_text.strip())
                    if not title or not 1888 <= year <= 2200:
                        raise ValueError
                    if peer.recommend_movie(title, year):
                        print(f"[Movie] You recommended {title} ({year})")
                    else:
                        print(
                            "Invalid recommendation or you already recommended this movie."
                        )
                except ValueError:
                    print(
                        "Usage: /movie TITLE | YEAR  (example: /movie The Matrix | 1999)"
                    )
            elif line.startswith("/connect "):
                parts = line.split()
                if len(parts) == 3:
                    try:
                        peer.connect(parts[1], int(parts[2]))
                    except ValueError:
                        print("Port must be a number.")
                else:
                    print("Usage: /connect HOST PORT")
            elif line:
                print(
                    "Unknown command. Use /all, /msg, /create, /join, /say, /leave, /rooms, /movie, /movies, /peers, /connect, or /quit."
                )
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        peer.close()


if __name__ == "__main__":
    main()
