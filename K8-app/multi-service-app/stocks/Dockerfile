FROM python:alpine3.12
WORKDIR /app
COPY . /app
RUN pip install Flask requests pymongo
ENV FLASK_APP=app.py
ENV FLASK_RUN_PORT=8000
ENV NINJA_API_KEY='ADD YOUR API KEY HERE'
CMD ["flask", "run", "--host=0.0.0.0"]


