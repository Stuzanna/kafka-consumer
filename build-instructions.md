# Docker Build Help
Commands used when building.

docker build -t kafka-consumer:0.x -f ./Dockerfile ./

docker login --username stuzanne
docker tag kafka-data-generator:0.x stuzanne/kafka-consumer:0.x
docker push stuzanne/kafka-consumer:0.x

docker tag stuzanne/kafka-consumer:0.x stuzanne/kafka-consumer:latest
docker push stuzanne/kafka-consumer:latest
