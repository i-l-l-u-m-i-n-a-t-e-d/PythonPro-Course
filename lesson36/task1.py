APP = r'''
print("Hello, Docker!")
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
COPY main.py .
CMD ["python", "main.py"]
'''

COMMANDS = r'''
docker build -t lesson37-task1 .
docker run --rm lesson37-task1
'''
