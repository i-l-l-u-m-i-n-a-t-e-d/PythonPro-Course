APP = r'''
import os

name = os.getenv("NAME", "Docker")
print(f"Hello, {name}!")
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
COPY main.py .
CMD ["python", "main.py"]
'''

COMMANDS = r'''
docker build -t lesson37-task2 .
docker run --rm -e NAME=Ania lesson37-task2
docker run --rm -e NAME=Kuba lesson37-task2
'''
