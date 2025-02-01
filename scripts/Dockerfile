FROM python:3.10-slim-buster

# Copy in pip requirements
COPY ./requirements.txt requirements.txt
# Install python packages
RUN pip install --no-cache-dir --upgrade -r requirements.txt

WORKDIR /scripts
# Copy Repo into Docker Container
COPY . .

CMD ["sh", "-c", "python producer.py"]