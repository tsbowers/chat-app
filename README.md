# CSE 310 — Module 1: Networking
## Multi-User Chat Application
## video demo https://www.loom.com/share/ae5baa315ff24282bf1b2e3d42e280fb
## Overview
For this module, I built a multi-user chat application in Python using
the `socket` and `threading` libraries. It follows the client-server
model — a server accepts connections from multiple clients, relays chat
messages between everyone connected, and logs every message to a local
SQLite database.

I chose a chat app instead of my original idea (a home network monitor)
because it sets up better for my next two sprints: a mobile app sprint
and a cloud database sprint. I designed the message protocol to be
simple and language-agnostic (JSON over TCP) so I can build a mobile
client against the same server later without changing the networking
code, and swap the local database for a cloud one without touching the
protocol.

## Model Used: Client-Server
- **`server.py`** — accepts multiple client connections at once (a
  separate thread per client), relays chat messages to everyone
  connected, and logs each message to a SQLite database
  (`chat_history.db`).
- **`client.py`** — connects to the server, sends a username, and lets
  the user send and receive messages from the command line.

## Protocol
Every message sent over the socket is a single line of JSON, ending in
`\n`. I used this format because TCP only guarantees a stream of bytes,
not message boundaries, so both sides need an agreed-upon way to know
where one message ends and the next begins.

**Client → Server**
| Type   | Fields     | Purpose                                  |
|--------|------------|-------------------------------------------|
| `JOIN` | `username` | Announce a username when connecting       |
| `MSG`  | `text`     | Send a chat message to everyone           |
| `LIST` | —          | Request the list of users currently online |
| `QUIT` | —          | Disconnect gracefully                     |

**Server → Client**
| Type       | Fields                    | Purpose                            |
|------------|---------------------------|--------------------------------------|
| `SYSTEM`   | `text`                    | Join/leave notices, welcome message  |
| `MSG`      | `username`, `text`, `time`| A relayed chat message               |
| `USERLIST` | `users` (list)            | Response to a `LIST` request         |

## Requirements This Satisfies
- **Basic requirement:** A client sends a request (`MSG`, `LIST`, etc.)
  to the server, the server processes it, and sends a response back
  that the client displays.
- **Transport:** TCP — I chose this over UDP because chat needs reliable,
  in-order delivery.
- **Additional requirements (I implemented two):**
  1. **Three or more request types** — `JOIN`, `MSG`, `LIST`, `QUIT`
     (four total).
  2. **Local file/database use** — every message is logged to a SQLite
     database with the username, message text, and timestamp.

## How to Run It
You need two terminal windows open (or two computers on the same
network).

1. Start the server:
   ```
   python3 server.py
   ```
   It listens on port `5050` by default.

2. Start one or more clients:
   ```
   python3 client.py
   ```
   Enter a username when prompted, then type messages and press Enter.

3. Client commands:
   - Type a message + Enter → sends it to everyone connected.
   - `/list` → shows who is currently online.
   - `/quit` → disconnects from the server.