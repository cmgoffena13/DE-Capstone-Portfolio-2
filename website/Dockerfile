FROM python:3.10-slim-buster
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1
# Copy in pip requirements
COPY ./requirements.txt requirements.txt
# Install python packages
RUN pip install --no-cache-dir --upgrade -r requirements.txt
# Set working directory in container
WORKDIR /producer_ui
# Copy Repo into Docker Container
COPY . .
# Expose Gunicorn port
EXPOSE 8000
# Trigger Gunicorn Server
CMD ["gunicorn", "-c", "python:config.gunicorn", "startup:app"]