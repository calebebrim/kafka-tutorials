install:
	pip install -r requirements.txt
	pip install gunicorn
  
dev:
	python main.py --num-backend-threads 5 --metrics-port 80080



dev-backend:
	python main.py --no-http --num-backend-threads 5 --metrics-port 8008

dev-rest: 
	python main.py --no-backend --metrics-port 8000 -l INFO





run:
# -w 4: Use 4 worker processes for handling requests.
# -b 0.0.0.0:5000: Binds to port 5000.
	gunicorn -w 4 -b 0.0.0.0:5000 kafka_http_router:app
