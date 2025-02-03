from kcp import KCPClientSync

client = KCPClientSync(
    "127.0.0.1",
    9999,
    conv_id=1,
    no_delay=True,
    update_interval=10,
    resend_count=5,
    no_congestion_control=True,
    receive_window_size=1024,
    send_window_size=1024
)


@client.on_data
def handle_data(data: bytes) -> None:
    print(data)


@client.on_start
def on_start() -> None:
    print("Connected to server!")

    while True:
        client.send(b"Data!")


client.start()