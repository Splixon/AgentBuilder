import asyncio

class Greeter:
    def __init__(self, name: str) -> None:
        self.name = name

    async def greet(self) -> str:
        # Simulate some time-consuming operation
        await asyncio.sleep(1)
        return f'Hello, {self.name}!'

async def main() -> None:
    user_name = input('Please enter your name: ')
    greeter = Greeter(user_name)
    print(await greeter.greet())

if __name__ == '__main__':
    asyncio.run(main())
