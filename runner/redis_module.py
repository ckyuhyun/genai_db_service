import asyncio
import logging
import json
from unittest import runner
from fastapi.concurrency import asynccontextmanager
import redis.asyncio as asyncredis
from fastapi import FastAPI
from postgres_rag_sync import DBSync

from config import redis_host, redis_port, redis_password, redis_default_key_name


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

postgres_rag_sync = DBSync()


async def _handle_event(incoming_data : dict, 
                  postgres_rag_sync: DBSync):
    """
        Handle the incoming event data and push it to Postgres.
    """
    event_dict = json.loads(incoming_data)
    thread_id = event_dict.get('thread_id')
    event_data = event_dict.get('data', {})

    print(f"[*] Processing Event: {thread_id} : {event_data}")


    meta_data = event_dict.get("metadata", {})

    await postgres_rag_sync.push(thread_id=thread_id,
                                 event_id=thread_id,
                                 content=event_data)
    
    

def redis_check_connect(redis_client) -> bool:
    """
        Check the connection to Redis by sending a PING command.
    """
    try:
        return redis_client.ping()        
    except:
        return False
        


async def redis_connect() :
    """
        Connect to Redis and return the client.
    """
    redis_client = asyncredis.Redis(host=redis_host, 
                                   port=redis_port, 
                                   password=redis_password, 
                                   decode_responses=True)
    return redis_client

async def redis_listener(app:FastAPI):
    logger.info("Connect to redis subscription")

    try:
        redis_client = await redis_connect()
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(redis_default_key_name)
        

        logger.info(f"Subscribed to Redis channel: {redis_default_key_name}")

        while True:

            if redis_check_connect(redis_client) is False:
                logger.warning("Redis connection lost. Attempting to reconnect...")

                redis_client = redis_connect()
                pubsub = redis_client.pubsub()
                pubsub.subscribe(redis_default_key_name)
                logger.info(f"Reconnected and subscribed to Redis channel: {redis_default_key_name}")
            
            message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            
            if message:
                try:                    
                    await _handle_event(message['data'], 
                                        postgres_rag_sync)
                    
                    logger.info(f"Received message from Redis: {message['data']}")
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to decode JSON message: {e}")                    
                except Exception as e:
                    logger.error(f"Unexpected error while processing message: {e}")
            
            await asyncio.sleep(0.01)  # Small sleep to prevent busy waiting
    except asyncio.CancelledError:
        logger.info("Redis listener task was cancelled.")
    finally:
        await pubsub.unsubscribe(redis_default_key_name)
        await redis_client.close()
        logger.info("Unsubscribed from Redis channel and closed connection.")
    

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Starting up
    listener_task = asyncio.create_task(redis_listener(app))
    yield

    # Shutting down
    listener_task.cancel()
    await asyncio.gather(listener_task, return_exceptions=True)


    
