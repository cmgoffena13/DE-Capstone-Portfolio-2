#!/bin/bash

# Start the job manager
./bin/jobmanager.sh start-foreground &

# Wait for the JobManager to be fully initialized
sleep 10

# Submit the Flink job
./bin/flink run -py /opt/src/job/consumer.py --pyFiles /opt/src -d

# Keep the container running after job submission
tail -f /dev/null