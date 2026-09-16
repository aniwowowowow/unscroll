import os
from dotenv import load_dotenv
from sqlalchemy.engine.url import make_url
import pg8000

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found -- check your .env file exists and is filled in")

# pg8000's native connect() wants individual pieces (host, user, password, etc.)
# rather than one connection-string URL, so we parse DATABASE_URL apart here.
url = make_url(DATABASE_URL)

try:
    connection = pg8000.connect(
        user=url.username,
        password=url.password,
        host=url.host,
        port=url.port or 5432,
        database=url.database,
    )
    cursor = connection.cursor()

    cursor.execute("SELECT version();")
    result = cursor.fetchone()

    print("Connected successfully!")
    print("Postgres version:", result[0])

    cursor.close()
    connection.close()

except Exception as e:
    print("Connection failed:")
    print(e)