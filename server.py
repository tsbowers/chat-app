"""
server.py - Multi-client TCP chat server

Protocol:
    Each message sent over the socket is a single line of JSON, terminated
    by '\n'. This keeps message boundaries clear over a TCP stream.

    Client -> Server message types:
        {"type": "JOIN", "username": "<name>"}
        {"type": "MSG",  "text": "<message text>"}
        {"type": "LIST"}
        {"type": "QUIT"}

    Server -> Client message types:
        {"type": "SYSTEM", "text": "<info message>"}
        {"type": "MSG", "username": "<sender>", "text": "<message>", "time": "<HH:MM:SS>"}
        {"type": "USERLIST", "users": ["alice", "bob"]}
"""

import socket
import threading
import sqlite3
import json
import datetime

HOST = "0.0.0.0"
PORT = 5050
DB_FILE = "chat_history.db"

# Shared state across client threads
clients_lock = threading.Lock()
clients = {}  # {connection: username}


def init_db():
    """Create the messages table if it doesn't already exist."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            text TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )
    conn.commit()
    conn.close()


def log_message(username, text):
    """Persist a chat message to the local SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.execute(
        "INSERT INTO messages (username, text, timestamp) VALUES (?, ?, ?)",
        (username, text, datetime.datetime.now().isoformat(timespec="seconds")),
    )
    conn.commit()
    conn.close()


def send_json(conn, payload):
    """Send a dict to a client as a newline-terminated JSON line."""
    data = (json.dumps(payload) + "\n").encode("utf-8")
    try:
        conn.sendall(data)
    except OSError:
        pass  # client already disconnected; cleanup happens elsewhere


def broadcast(payload, exclude_conn=None):
    """Send a message to every connected client (optionally skip one)."""
    with clients_lock:
        for conn in list(clients.keys()):
            if conn is not exclude_conn:
                send_json(conn, payload)


def remove_client(conn):
    """Remove a client from the registry and announce their departure."""
    with clients_lock:
        username = clients.pop(conn, None)
    if username:
        print(f"[DISCONNECT] {username} left.")
        broadcast({"type": "SYSTEM", "text": f"{username} has left the chat."})
    try:
        conn.close()
    except OSError:
        pass


def handle_client(conn, addr):
    """Thread target: handles the full lifecycle of one client connection."""
    buffer = ""
    username = None
    try:
        while True:
            chunk = conn.recv(4096)
            if not chunk:
                break  # client closed the connection
            buffer += chunk.decode("utf-8")

            # A TCP stream can deliver multiple lines (or partial lines) at
            # once, so split on newlines and keep any leftover in buffer.
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                message = json.loads(line)
                msg_type = message.get("type")

                if msg_type == "JOIN":
                    username = message.get("username", f"user{addr[1]}")
                    with clients_lock:
                        clients[conn] = username
                    print(f"[CONNECT] {username} joined from {addr}")
                    broadcast(
                        {"type": "SYSTEM", "text": f"{username} has joined the chat."},
                        exclude_conn=conn,
                    )
                    send_json(conn, {"type": "SYSTEM", "text": f"Welcome, {username}!"})

                elif msg_type == "MSG":
                    text = message.get("text", "")
                    if username is None:
                        send_json(conn, {"type": "SYSTEM", "text": "Join before sending messages."})
                        continue
                    log_message(username, text)
                    timestamp = datetime.datetime.now().strftime("%H:%M:%S")
                    broadcast(
                    {"type": "MSG", "username": username, "text": text, "time": timestamp},
                    exclude_conn=conn,
                    )

                elif msg_type == "LIST":
                    with clients_lock:
                        names = list(clients.values())
                    send_json(conn, {"type": "USERLIST", "users": names})

                elif msg_type == "QUIT":
                    return  # falls through to finally block for cleanup

                else:
                    send_json(conn, {"type": "SYSTEM", "text": f"Unknown message type: {msg_type}"})

    except (ConnectionResetError, json.JSONDecodeError) as e:
        print(f"[ERROR] {addr}: {e}")
    finally:
        remove_client(conn)


def main():
    init_db()
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[LISTENING] Chat server running on {HOST}:{PORT}")

    try:
        while True:
            conn, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
            thread.start()
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Server stopping.")
    finally:
        server.close()


if __name__ == "__main__":
    main()
