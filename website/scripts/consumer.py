from influxdb_client import InfluxDBClient
from influxdb_client.client.write_api import SYNCHRONOUS
from pyflink.datastream import StreamExecutionEnvironment
from pyflink.datastream.functions import SinkFunction
from pyflink.table import EnvironmentSettings, StreamTableEnvironment


class GenericInfluxDBSink(SinkFunction):
    def __init__(self, url, bucket, measurement, tag_key):
        self.client = InfluxDBClient(url=url, token=None, org=None)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)
        self.bucket = bucket
        self.measurement = measurement
        self.tag_key = tag_key

    def invoke(self, value, context):
        """
        Convert Flink records to InfluxDB points and write them.
        """
        point = {
            "measurement": self.measurement,
            "tags": {self.tag_key: value[self.tag_key]},
            "fields": {
                k: float(v) if isinstance(v, (int, float)) else v
                for k, v in value.items()
                if k != "event_timestamp"
            },
            "time": int(value["event_timestamp"].timestamp() * 1000),
        }
        self.write_api.write(bucket=self.bucket, record=point)

    def close(self):
        self.client.close()


def create_influxdb_sink(data_stream, measurement, tag_key):
    influxdb_url = "http://influxdb:8086"
    bucket = "events"

    data_stream.add_sink(
        GenericInfluxDBSink(influxdb_url, bucket, measurement, tag_key)
    )


def create_stock_prices_source_kafka(t_env):
    kafka_url = "kafka:9092"  # Kafka service inside Docker Compose, using the service name 'kafka'
    topic = "stock-prices"  # Topic name
    pattern = "yyyy-MM-dd''T''HH:mm:ss.SS''Z''"

    # Define the source table creation DDL for the stock-prices topic
    source_ddl = f"""
        CREATE TABLE stock_prices (
            event_type VARCHAR,
            symbol VARCHAR,
            volume INT,
            accumulated_volume INT,
            official_open_price DECIMAL(20,4),
            vwap DECIMAL(20,4),
            open DECIMAL(20,4),
            close DECIMAL(20,4),
            high DECIMAL(20,4),
            low DECIMAL(20,4),
            aggregate_vwap DECIMAL(20,4),
            average_size INT,
            start_timestamp BIGINT,
            end_timestamp BIGINT,
            otc VARCHAR,
            event_timestamp AS TO_TIMESTAMP(end_timestamp, '{pattern}')
        ) WITH (
            'connector' = 'kafka',
            'properties.bootstrap.servers' = '{kafka_url}',
            'topic' = '{topic}',
            'properties.group.id' = 'flink-consumer',
            'scan.startup.mode' = 'latest-offset',
            'properties.auto.offset.reset' = 'latest',
            'format' = 'json'
        );
    """
    print(source_ddl)
    t_env.execute_sql(source_ddl)
    return "stock_prices"


def create_news_articles_source_kafka(t_env):
    kafka_url = "kafka:9092"  # Kafka service inside Docker Compose, using the service name 'kafka'
    topic = "news-articles"  # Topic name
    pattern = "yyyy-MM-dd''T''HH:mm:ss.SS''Z''"  # Timestamp format for event_timestamp

    # Define the source table creation DDL for the stock-prices topic
    source_ddl = f"""
        CREATE TABLE news_articles (
            id VARCHAR,
            type VARCHAR,
            sectionId VARCHAR,
            sectionName VARCHAR,
            webPublicationDate VARCHAR,
            webTitle VARCHAR,
            webUrl VARCHAR,
            apiUrl VARCHAR,
            isHosted BOOLEAN,
            pillarId VARCHAR,
            pillarName VARCHAR,
            event_timestamp AS TO_TIMESTAMP(webPublicationDate, '{pattern}')
        ) WITH (
            'connector' = 'kafka',
            'properties.bootstrap.servers' = '{kafka_url}',
            'topic' = '{topic}',
            'properties.group.id' = 'flink-consumer',
            'scan.startup.mode' = 'latest-offset',
            'properties.auto.offset.reset' = 'latest',
            'format' = 'json'
        );
    """
    print(source_ddl)
    t_env.execute_sql(source_ddl)
    return "news_articles"


def event_processing():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(2)  # Can increase

    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()

    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    stock_prices_source = create_stock_prices_source_kafka(t_env=t_env)
    news_articles_source = create_news_articles_source_kafka(t_env=t_env)

    # Convert Flink tables to data streams
    stock_prices_stream = t_env.from_path(stock_prices_source)
    news_articles_stream = t_env.from_path(news_articles_source)

    # Add sinks for both data streams
    create_influxdb_sink(
        stock_prices_stream, measurement="stock_prices", tag_key="symbol"
    )
    create_influxdb_sink(
        news_articles_stream, measurement="news_articles", tag_key="search"
    )

    t_env.execute("Flink to InfluxDB")


if __name__ == "__main__":
    event_processing()
