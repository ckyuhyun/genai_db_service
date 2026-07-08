import os
from dotenv import load_dotenv

load_dotenv()


redis_host = os.getenv('Redis_Host')
redis_port = os.getenv('Redis_Port')
redis_password = os.getenv('Redis_Password')
redis_default_key_name = os.getenv('Redis_Default_Key')


