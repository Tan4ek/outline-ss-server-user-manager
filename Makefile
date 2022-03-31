up:
	uvicorn --host 0.0.0.0 --port 8080 main:app

up-dev:
	uvicorn --host 0.0.0.0 --port 8080 main:app --reload

