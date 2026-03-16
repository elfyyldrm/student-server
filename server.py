import socket

HOST = "0.0.0.0"
PORT = 5000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.bind((HOST, PORT))
    server.listen()

    print("Server started")

    while True:
        conn, addr = server.accept()
        with conn:
            print("Connected:", addr)

            data = conn.recv(1024)
            if not data:
                continue

            print("Received:", data.decode())
            conn.sendall(b"Hello client")
