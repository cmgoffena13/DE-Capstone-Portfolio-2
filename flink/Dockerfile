FROM flink:1.20.0

# install python3 and pip3
RUN apt-get update -y && \
        apt-get install -y python3 python3-pip python3-dev wget && \
        rm -rf /var/lib/apt/lists/*
        
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy requirements.txt from website directory
COPY ../website/requirements.txt /tmp/requirements.txt
# Copy .env file for InfluxDB Token
COPY ../website/.env /opt/src/job/.env

# Install Python dependencies
RUN python -m pip install --upgrade pip; \
        pip install -r /tmp/requirements.txt

# Get Kafka Connector
RUN wget -P /opt/flink/lib/ https://repo.maven.apache.org/maven2/org/apache/flink/flink-sql-connector-kafka/3.4.0-1.20/flink-sql-connector-kafka-3.4.0-1.20.jar;
WORKDIR /opt/flink