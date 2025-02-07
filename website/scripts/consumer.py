from influxdb_client import InfluxDBClient, WriteOptions
from pyflink.common.typeinfo import Types
from pyflink.datastream import (
    ProcessFunction,
    RuntimeContext,
    StreamExecutionEnvironment,
)
from pyflink.table import EnvironmentSettings, StreamTableEnvironment


class InfluxDBSink(ProcessFunction):
    def __init__(self, url, bucket, measurement, tag_key):
        self.url = url
        self.bucket = bucket
        self.measurement = measurement
        self.tag_key = tag_key
        self.client = None
        self.write_api = None

    def open(self, context: RuntimeContext):
        self.client = InfluxDBClient(url=self.url, token=None, org=None)
        self.write_api = self.client.write_api(
            write_options=WriteOptions(synchronous=True)
        )

    def process_element(self, value, context: "ProcessFunction.Context"):
        point = {
            "measurement": self.measurement,
            "tags": {self.tag_key: value[self.tag_key]},
            "fields": {
                k: float(v) if isinstance(v, (int, float)) else v
                for k, v in value.items()
                if k != "event_timestamp"
            },
            "time": int(
                value["event_timestamp"].timestamp() * 1000
            ),  # Convert timestamp
        }
        self.write_api.write(bucket=self.bucket, record=point)

    def close(self):
        if self.client:
            self.client.close()


def create_influxdb_sink(data_stream, measurement, tag_key):
    influxdb_url = "http://influxdb:8086"
    bucket = "events"
    influx_sink = InfluxDBSink(influxdb_url, bucket, measurement, tag_key)
    data_stream.process(influx_sink)


def create_stock_prices_source_kafka(t_env):
    kafka_url = "kafka:9092"
    topic = "stock-prices"

    source_ddl = f"""
        CREATE TABLE stock_prices (
            event_type VARCHAR,
            symbol VARCHAR,
            volume INT,
            accumulated_volume INT,
            official_open_price DOUBLE,
            vwap DOUBLE,
            `open` DOUBLE,
            `close` DOUBLE,
            high DOUBLE,
            low DOUBLE,
            aggregate_vwap DOUBLE,
            average_size INT,
            start_timestamp BIGINT,
            end_timestamp BIGINT,
            otc VARCHAR,
            event_timestamp AS CAST(FROM_UNIXTIME(end_timestamp / 1000) AS TIMESTAMP(3))
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
    print("Executing SQL: ", source_ddl)
    t_env.execute_sql(source_ddl)
    return "stock_prices"


def create_news_articles_source_kafka(t_env):
    kafka_url = "kafka:9092"
    topic = "news-articles"
    pattern = "yyyy-MM-dd''T''HH:mm:ss.SS''Z''"

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
    print("Executing SQL: ", source_ddl)
    t_env.execute_sql(source_ddl)
    return "news_articles"


def event_processing():
    env = StreamExecutionEnvironment.get_execution_environment()
    env.enable_checkpointing(10 * 1000)
    env.set_parallelism(1)  # Can increase

    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()

    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    stock_prices_source = create_stock_prices_source_kafka(t_env=t_env)
    news_articles_source = create_news_articles_source_kafka(t_env=t_env)

    # Convert Flink tables to data streams
    stock_prices_table = t_env.from_path(stock_prices_source)
    news_articles_table = t_env.from_path(news_articles_source)

    # Declare stream schema (kind of lame)
    stock_prices_type_info = Types.ROW_NAMED(
        [
            "event_type",
            "symbol",
            "volume",
            "accumulated_volume",
            "official_open_price",
            "vwap",
            "open",
            "close",
            "high",
            "low",
            "aggregate_vwap",
            "average_size",
            "start_timestamp",
            "end_timestamp",
            "otc",
            "event_timestamp",
        ],
        [
            Types.STRING(),
            Types.STRING(),
            Types.INT(),
            Types.INT(),
            Types.DOUBLE(),
            Types.DOUBLE(),
            Types.DOUBLE(),
            Types.DOUBLE(),
            Types.DOUBLE(),
            Types.DOUBLE(),
            Types.DOUBLE(),
            Types.INT(),
            Types.LONG(),
            Types.LONG(),
            Types.STRING(),
            Types.SQL_TIMESTAMP(),
        ],
    )

    news_articles_type_info = Types.ROW_NAMED(
        [
            "id",
            "type",
            "sectionId",
            "sectionName",
            "webPublicationDate",
            "webTitle",
            "webUrl",
            "apiUrl",
            "isHosted",
            "pillarId",
            "pillarName",
            "event_timestamp",
        ],
        [
            Types.STRING(),
            Types.STRING(),
            Types.STRING(),
            Types.STRING(),
            Types.STRING(),
            Types.STRING(),
            Types.STRING(),
            Types.STRING(),
            Types.BOOLEAN(),
            Types.STRING(),
            Types.STRING(),
            Types.SQL_TIMESTAMP(),
        ],
    )

    # Convert tables to data streams
    stock_prices_stream = t_env.to_append_stream(
        stock_prices_table, type_info=stock_prices_type_info
    )
    news_articles_stream = t_env.to_append_stream(
        news_articles_table, type_info=news_articles_type_info
    )

    # Add sinks for both data streams
    create_influxdb_sink(
        data_stream=stock_prices_stream, measurement="stock_prices", tag_key="symbol"
    )
    create_influxdb_sink(
        data_stream=news_articles_stream, measurement="news_articles", tag_key="search"
    )

    env.execute("Kafka to InfluxDB")


if __name__ == "__main__":
    event_processing()
