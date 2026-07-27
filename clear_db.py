import os
import asyncio
from app.database import init_db

async def reset_database():
    db_file = "automail.db"
    if os.path.exists(db_file):
        os.remove(db_file)
        print("automail.db file deleted!")
    
    await init_db()
    print("Database freshly initialized with zero accounts!")

if __name__ == "__main__":
    asyncio.run(reset_database())
