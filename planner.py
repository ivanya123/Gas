from apscheduler.schedulers.asyncio import AsyncIOScheduler

from new import main
main_sheduler = AsyncIOScheduler()

main_sheduler.add_job(main, trigger='interval', seconds=15)

main_sheduler.start()