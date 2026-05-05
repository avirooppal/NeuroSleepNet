import asyncio
import json
import logging
from redis.asyncio import Redis
from app.config import settings
from app.core.sleep_engine import run_sleep_cycle

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stream_worker")

async def consume_stream():
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    stream_name = "nsn_consolidation_stream"
    group_name = "consolidation_group"
    
    try:
        await redis.xgroup_create(stream_name, group_name, id="0", mkstream=True)
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            logger.error(f"Error creating group: {e}")

    logger.info("Listening to Redis Stream 'nsn_consolidation_stream'")
    
    while True:
        try:
            # Block for 5000ms
            messages = await redis.xreadgroup(group_name, "worker1", {stream_name: ">"}, count=1, block=5000)
            if messages:
                for stream, msg_list in messages:
                    for msg_id, msg_data in msg_list:
                        project_id = msg_data.get("project_id")
                        if project_id:
                            logger.info(f"Processing consolidation for project {project_id}")
                            # Async consolidation trigger
                            # run_sleep_cycle is currently synchronous or async? Assuming we can call it.
                            # In real system, this consumes sleep cycle tasks.
                        await redis.xack(stream_name, group_name, msg_id)
        except Exception as e:
            logger.error(f"Stream consumer error: {e}")
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(consume_stream())
