APP = r'''
from aiohttp import web

async def hello(request):
    return web.Response(text="Hello from Docker!")

app = web.Application()
app.router.add_get("/", hello)
web.run_app(app, host="0.0.0.0", port=8000)
'''

DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir aiohttp
COPY main.py .
EXPOSE 8000
CMD ["python", "main.py"]
'''

COMMANDS = r'''
docker build -t lesson37-task3 .
docker run --rm -p 3000:8000 lesson37-task3
# test: http://localhost:3000/
'''
