APP = r'''
from datetime import datetime
from pathlib import Path
import time

log_file = Path("/data/app.log")
log_file.parent.mkdir(parents=True, exist_ok=True)
while True:
    with log_file.open("a", encoding="utf-8") as file:
        file.write(f"{datetime.now().isoformat()} container is running\n")
    time.sleep(5)
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
COPY logger.py .
CMD ["python", "logger.py"]
'''

COMMANDS = r'''
docker build -t lesson37-task4 .
docker volume create lesson37-task4-logs
docker run -d --name lesson37-task4 --mount source=lesson37-task4-logs,target=/data lesson37-task4
sleep 6
docker rm -f lesson37-task4
docker run -d --name lesson37-task4 --mount source=lesson37-task4-logs,target=/data lesson37-task4
docker exec lesson37-task4 cat /data/app.log
'''
