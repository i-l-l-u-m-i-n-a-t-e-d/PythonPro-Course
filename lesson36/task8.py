COMMANDS = r'''
docker network create lesson37-task8-net
docker run -d --name lesson37-task8-a --network lesson37-task8-net alpine:latest sleep infinity
docker run --rm --network lesson37-task8-net alpine:latest ping -c 2 lesson37-task8-a
docker rm -f lesson37-task8-a
docker network rm lesson37-task8-net
'''
