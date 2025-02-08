import asyncio
from asyncio import CancelledError

async def delay(delay_seconds: int) -> int:
    print(f'Засыпаю на {delay_seconds} секунд')
    await asyncio.sleep(delay_seconds)
    print(f'сон в течении {delay_seconds} секунд закончился')
    return delay_seconds

#
# async def helli_every_seconf():
#     for i in range(2):
#         await asyncio.sleep(1)
#         print('Пока я жду выполняется другой код')




async def main():
    long_task = asyncio.create_task(delay(5))
    seconds = 0

    while not long_task.done():
        print(f'Задача не закончилась {long_task}')
        await asyncio.sleep(1)
        seconds += 1
        if seconds == 5:
            long_task.cancel()
    print('Задача закончилась')


    try:
        await long_task
    except CancelledError:
        print('Задача была отменена')



if __name__ == '__main__':
    asyncio.run(main())