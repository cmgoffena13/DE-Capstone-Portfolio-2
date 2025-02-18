import logging
import os
import sys
from os.path import abspath, dirname, join

from dotenv import load_dotenv
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pyflink.common.typeinfo import Types
from pyflink.common.types import Row
from pyflink.datastream import (
    ProcessFunction,
    RuntimeContext,
    StreamExecutionEnvironment,
)
from pyflink.table import EnvironmentSettings, StreamTableEnvironment

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)

base_dir = abspath(dirname(dirname(__file__)))
load_dotenv(join(base_dir, ".env"))

try:
    INFLUXDB_TOKEN = os.environ["INFLUXDB_TOKEN"]
except KeyError:
    raise KeyError(f"Missing. Path is: {base_dir} + /.env - Check for file existence")

LOCAL = int(os.environ["LOCAL"])

if LOCAL == 1:
    influxdb_url = "http://influxdb:8086"
    kafka_url = "kafka:9092"
    logger.info("Local Config Initialized")
else:
    influxdb_url = os.environ.get("INFLUXDB_URL")
    logger.info("Confluent Config Initialized")
    logger.info("Flink Container not needed, exiting job")
    sys.exit(0)


class InfluxDBSink(ProcessFunction):
    def __init__(self, measurement):
        self.url = influxdb_url
        self.bucket = "events"
        self.org = "NA"
        self.measurement = measurement
        self.client = None
        self.write_api = None
        self.token = INFLUXDB_TOKEN

    def open(self, context: RuntimeContext):
        logger.info("Opening RunTimeContext...")
        self.client = InfluxDBClient(url=self.url, token=self.token, org=self.org)
        self.write_api = self.client.write_api(write_options=SYNCHRONOUS)

    def process_element(self, value, context: "ProcessFunction.Context"):
        if isinstance(value, Row):
            row_dict = {field: value[field] for field in value.as_dict()}
            p = Point(self.measurement)

            for k, v in row_dict.items():
                if k == "event_timestamp":
                    p.time(
                        int(v.timestamp() * 1_000_000_000)
                    )  # Ensure nanosecond precision
                if k in {"symbol", "search"}:
                    p.tag("key", str(v))
                    logger.info(f"Kafka Key is: {str(v)}")
                elif isinstance(v, (int, float)):
                    p.field(k, float(v))
                else:
                    p.field(k, str(v))

            try:
                logger.info(f"Writing record to InfluxDB, {self.bucket}: {p}")
                self.write_api.write(bucket=self.bucket, org=self.org, record=p)
                logger.info("Record written successfully.")
            except Exception as e:
                raise Exception(f"Error writing to InfluxDB: {e}; Failed record: {p}")
        else:
            raise ValueError(
                f"Expected value to be a Row, but got {type(value)}. Received Value: {value}"
            )

    def close(self):
        if self.client:
            logger.info("Closing RunTimeContext...")
            self.client.close()


def create_influxdb_sink(data_stream, measurement):
    logger.info("Starting InfluxDB Sink")
    influx_sink = InfluxDBSink(measurement)
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
    pattern = "yyyy-MM-dd''T''HH:mm:ss''Z''"

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
            `search` VARCHAR,
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
    # env.enable_checkpointing(10 * 1000)
    env.set_parallelism(2)  # Can increase

    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()

    t_env = StreamTableEnvironment.create(env, environment_settings=settings)

    stock_prices_source_name = create_stock_prices_source_kafka(t_env=t_env)
    news_articles_source_name = create_news_articles_source_kafka(t_env=t_env)

    # Convert Flink tables to data streams
    stock_prices_table = t_env.from_path(stock_prices_source_name)
    news_articles_table = t_env.from_path(news_articles_source_name)

    # result = t_env.execute_sql("""SELECT kafka_key FROM news_articles""")
    # for row in result.collect():
    #     logger.info(f"kafka key from flink table: {row}")

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
            "search",
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
    create_influxdb_sink(data_stream=stock_prices_stream, measurement="stock_prices")
    create_influxdb_sink(data_stream=news_articles_stream, measurement="news_articles")

    env.execute("Kafka to InfluxDB")


if __name__ == "__main__":
    event_processing()
