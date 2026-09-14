"""
client.py - Command-line TCP chat client

Connects to server.py, sends a JOIN message with a chosen username, then
lets the user type messages. A background thread listens for incoming
messages so the client can send and receive at the same time.

Commands typed by the user:
    /list   - ask the server who else is connected
    /quit   - disconnect gracefully
    anything else is sent as a regular chat message
"""

import socket
import threading
import json
import sys

HOST = "127.0.0.1"  # change to the server's IP address when testing on two machines
PORT = 5050


def send_json(sock, payload):
    """Send a dict to the server as a newline-terminated JSON line."""
    data = (json.dumps(payload) + "\n").encode("utf-8")
    sock.sendall(data)


def listen_for_messages(sock):
    """Background thread: continuously read and print messages from the server."""
    buffer = ""
    while True:
        try:
            chunk = sock.recv(4096)
        except OSError:
            break
        if not chunk:
            print("\n[DISCONNECTED] Server closed the connection.")
            break
        buffer += chunk.decode("utf-8")

        while "\n" in buffer:
            line, buffer = buffer.split("\n", 1)
            if not line.strip():
                continue
            message = json.loads(line)
            msg_type = message.get("type")

            if msg_type == "MSG":
                print(f"\n[{message['time']}] {message['username']}: {message['text']}\n> ", end="")
            elif msg_type == "SYSTEM":
                print(f"\n*** {message['text']} ***\n> ", end="")
            elif msg_type == "USERLIST":
                users = ", ".join(message.get("users", []))
                print(f"\n[ONLINE] {users}\n> ", end="")
            sys.stdout.flush()


def main():
    username = input("Choose a username: ").strip() or "anonymous"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOST, PORT))

    listener = threading.Thread(target=listen_for_messages, args=(sock,), daemon=True)
    listener.start()

    send_json(sock, {"type": "JOIN", "username": username})

    print("Connected. Type a message and press Enter. Use /list or /quit for commands.\n")
    try:
        while True:
            text = input("> ")
            if text.strip() == "/quit":
                send_json(sock, {"type": "QUIT"})
                break
            elif text.strip() == "/list":
                send_json(sock, {"type": "LIST"})
            elif text.strip():
                send_json(sock, {"type": "MSG", "text": text})
    except (KeyboardInterrupt, EOFError):
        send_json(sock, {"type": "QUIT"})
    finally:
        sock.close()
        print("Disconnected.")


if __name__ == "__main__":
    main()
