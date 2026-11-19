# P2P Chat

A decentralized movie-themed chat program written in Python 3 using only the standard library.

## Use case

Each user starts a peer node with a unique username and listening port. Users connect to other peers by IP address and port to exchange messages.

Users can send general group messages, private messages, and create or join movie-specific chat rooms. Users can also recommend movies, which are added to a shared recommendation ledger. Each recommendation gives a movie one point.

## Requirements

Python 3.9+. This implementation uses a direct TCP mesh as an alternative P2P architecture.

## Try it

Start three peers in separate terminals:

```bash
python chat.py --name Alice --port 5001
python chat.py --name Bob --port 5002 --connect 127.0.0.1 --peer-port 5001
python chat.py --name Charlie --port 5003 --connect 127.0.0.1 --peer-port 5001
```

Available commands:

- `/all Hello everyone` — Send a group message.
- `/msg Bob Hello` — Send a private message.
- `/peers` — List connected peers.
- `/connect 127.0.0.1 5001` — Connect to another peer.
- `/create The Matrix` — Create a movie chat room.
- `/join The Matrix` — Join a movie chat room.
- `/say Hello` — Send a message to your current room.
- `/leave` — Leave your current room.
- `/rooms` — List available rooms.
- `/whereami` — Show your current room and peer information.
- `/movie The Matrix | 1999` — Recommend a movie.
- `/movies` — View movie rankings.
- `/quit` — Exit the program.

## Protocol

Messages are newline-delimited UTF-8 JSON objects sent over TCP.

- `HELLO`: Exchanges peer information when connecting.
- `PEERS`: Shares known peers to build the network.
- `GROUP`: Sends a message to all connected peers.
- `PRIVATE`: Sends a message to a specific user.
- `ROOM_CREATE`: Announces a new movie chat room.
- `ROOM_SYNC`: Synchronizes available rooms.
- `ROOM_CHAT`: Sends messages to a movie room.
- `MOVIE`: Shares movie recommendations between peers.

Each message has a unique ID to prevent duplicate processing. Messages are forwarded between connected peers, allowing users to communicate without a central server.

Movie recommendations are stored locally and synchronized between peers. Each user can recommend a movie once, and the rankings are calculated from the total recommendations.

## Structure and limitations

- Everyone runs the same code with no centralized server.
- Users can send private and group messages.
- Users can create and join movie discussion rooms.
- Movie recommendations are shared and saved locally.
- Peers can disconnect and reconnect.
- Messages are not end-to-end encrypted.
- No authentication.
- No offline chat delivery or chat history.
- Peers must initially connect using an IP address and port.
- Movie rooms are not private or access-controlled.

## Files

- `chat.py` — User interface and commands.
- `peer.py` — P2P networking, messaging, and movie rooms.
- `ledger.py` — Movie recommendations and rankings.
- `README.md` — Project documentation.
