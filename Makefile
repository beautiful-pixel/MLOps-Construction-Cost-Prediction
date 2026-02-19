# build-api:
# 	docker build -t solafune-api -f ./src/api/Dockerfile .

# run-api:
# 	docker run --rm -d --name solafune-api -p 8000:8000 solafune-api

# stop-api:
# 	docker stop solafune-api

start-project:
	docker-compose -p mlops up -d --build

stop-project:
	docker-compose -p mlops down
