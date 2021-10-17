import asyncio 


async def tcp_client(message):
    reader, writer = await asyncio.open_connection(
        '127.0.0.1', 5566
    )
    print(f'Send: {message}')
    writer.write(message.encode())
    await writer.drain()

    data = await reader.read(100)
    print(f'Received from server: {data.decode()}')

    print('Close connection.')
    writer.close()
    await writer.wait_closed()
    


async def main():
    tasks = []
    for i in range(10):
        task = asyncio.create_task(tcp_client(f'message_{i}'))
        tasks.append(task)
    await asyncio.gather(*tasks) 
    """
    #requests = await asyncio.gather(*[tcp_client(f'message {i}') for i in range(5)])
    """



asyncio.run(main())
