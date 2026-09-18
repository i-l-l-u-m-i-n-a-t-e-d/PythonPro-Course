APP = r'''
from aiohttp import web

async def hello(request):
    return web.Response(text="Hello from Docker!")

app = web.Application()
app.router.add_get("/", hello)
web.run_app(app, host="0.0.0.0", port=8000)
'''

SINGLE_STAGE_DOCKERFILE = r'''
FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir aiohttp
COPY main.py .
EXPOSE 8000
CMD ["python", "main.py"]
'''

MULTI_STAGE_DOCKERFILE = r'''
FROM python:3.12-slim AS builder
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
RUN pip install --no-cache-dir aiohttp

FROM python:3.12-slim
COPY --from=builder /venv /venv
ENV PATH="/venv/bin:$PATH"
WORKDIR /app
COPY main.py .
EXPOSE 8000
CMD ["python", "main.py"]
'''

COMMANDS = r'''
docker build -f Dockerfile.single -t lesson37-task5-single .
docker build -f Dockerfile.multi -t lesson37-task5-multi .
docker image inspect lesson37-task5-single lesson37-task5-multi --format '{{.RepoTags}} {{.Size}}'
'''
