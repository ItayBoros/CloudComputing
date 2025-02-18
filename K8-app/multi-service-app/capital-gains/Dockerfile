FROM python:alpine3.12
WORKDIR /app
COPY . /app
RUN apk add --no-cache curl && pip install Flask requests
ENV FLASK_APP=app.py
ENV FLASK_RUN_PORT=8080
CMD ["flask", "run", "--host=0.0.0.0"]
