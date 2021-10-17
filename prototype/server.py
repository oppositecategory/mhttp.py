import asyncio 

async def handle_echo(reader, writer):
    data = await reader.read(100)
    message = data.decode()
    addr = writer.get_extra_info('peername')

    print(f'Received {message} from {addr}')
    print(f'Sending to client: {message}')
    writer.write(data)
    await writer.drain()

    print("Close the connection")
    writer.close()


async def main():
    server = await asyncio.start_server(
        handle_echo,'127.0.0.1',5566
    )
    addrs = ', '.join(str(sock.getsockname()) for sock in server.sockets)
    print(f'Servering on {addrs}')

    async with server:
        await server.serve_forever()

asyncio.run(main())