FROM flink:1.20.0

# install python3 and pip3
RUN apt-get update -y && \
apt-get install -y python3 python3-pip python3-dev && rm -rf /var/lib/apt/lists/*
RUN ln -s /usr/bin/python3 /usr/bin/python

# Copy requirements.txt from website directory
COPY ../website/requirements.txt /tmp/requirements.txt

# Install Python dependencies
RUN python -m pip install --upgrade pip; \
        pip install -r /tmp/requirements.txt