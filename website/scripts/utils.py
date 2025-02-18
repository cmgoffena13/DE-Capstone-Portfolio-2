import json
import random
import time
from dataclasses import asdict, dataclass, is_dataclass
from datetime import datetime, timezone
from os.path import abspath, dirname, join

import requests
from marshmallow import ValidationError
from marshmallow_dataclass import class_schema

base_dir = abspath(dirname(__file__))


def read_config():
    # reads the client configuration from client.properties
    # and returns it as a key-value map
    config = {}
    with open(join(base_dir, "client.properties")) as fh:
        for line in fh:
            line = line.strip()
            if len(line) != 0 and line[0] != "#":
                parameter, value = line.strip().split("=", 1)
                config[parameter] = value.strip()
    return config


def fetch_with_retries(url, params=None, max_retries=10, initial_delay=12):
    retries = 0
    while retries < max_retries:
        if params is not None:
            response = requests.get(url=url, params=params)
        else:
            response = requests.get(url)
        # exceeded api call limit; 429 Too Many Requests
        if response.status_code == 429:
            # Retry with exponential backoff
            # Add jitter for API calls to be randomly staggered
            jittered_delay = random.uniform(initial_delay - 1, initial_delay)
            expo = float(2**retries)
            wait_time = float(
                response.headers.get("Retry-After", jittered_delay * expo)
            )
            print(
                f"Rate Limited: Retrying in {wait_time:.2f}" + " "
                f"seconds... Function Retries Left: {max_retries - retries}"
            )
            time.sleep(wait_time)
            retries += 1
        elif response.status_code == 200:
            return response.json()
        else:
            response.raise_for_status()  # Raise an exception for other error codes
    raise Exception("Exceeded maximum retries for the API request")


@dataclass
class EquityAgg:
    event_type: str
    symbol: str
    volume: int
    accumulated_volume: int
    official_open_price: float
    vwap: float
    open: float
    close: float
    high: float
    low: float
    aggregate_vwap: float
    average_size: int
    start_timestamp: int
    end_timestamp: int
    otc: str = None  # Make optional in schema

    def __post_init__(self):
        schema = EquityAggSchema()
        errors = schema.validate(asdict(self))
        if errors:
            raise ValidationError(f"Validation errors: {errors}")

    def to_influx_json(
        self,
        measurement: str = "stock_prices",
        tag_fields: list = ["symbol"],
        time_field: str = "end_timestamp",
    ) -> dict:
        data = asdict(self)

        tags = {field: data[field] for field in tag_fields if field in data}

        time_value = int(data.get(time_field) * 1_000_000_000)

        fields = {k: v for k, v in data.items() if k != time_field}

        # Build the final JSON structure
        influx_json = {
            "measurement": measurement,
            "tags": tags,
            "time-field": time_value,
        }
        influx_json.update(fields)
        return influx_json


EquityAggSchema = class_schema(EquityAgg)


def equity_agg_to_json(equity_agg: EquityAgg):
    if is_dataclass(equity_agg):
        equity_agg_dict = asdict(equity_agg)
    elif isinstance(equity_agg, dict):
        equity_agg_dict = equity_agg
    else:
        raise ValueError("Expected a dataclass instance or dict")

    return json.dumps(equity_agg_dict, indent=4).encode("utf-8")


@dataclass
class Article:
    id: str
    type: str
    sectionId: str
    sectionName: str
    webPublicationDate: str
    webTitle: str
    webUrl: str
    apiUrl: str
    isHosted: bool
    pillarId: str
    pillarName: str
    search: str

    def __post_init__(self):
        schema = ArticleSchema()
        errors = schema.validate(asdict(self))
        if errors:
            raise ValidationError(f"Validation errors: {errors}")

    def to_influx_json(
        self,
        measurement: str = "news_articles",
        tag_fields: list = ["search"],
        time_field: str = "webPublicationDate",
    ) -> dict:
        data = asdict(self)

        tags = {field: data[field] for field in tag_fields if field in data}

        time_value = data.get(time_field)
        time_value = datetime.strptime(time_value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        time_value = int(time_value.timestamp() * 1_000_000)
        fields = {k: v for k, v in data.items() if k != time_field}

        # Build the final JSON structure
        influx_json = {
            "measurement": measurement,
            "tags": tags,
            "time-field": time_value,
        }
        influx_json.update(fields)
        return influx_json


ArticleSchema = class_schema(Article)


def article_to_json(article: Article):
    if is_dataclass(article):
        article_dict = asdict(article)
    elif isinstance(article, dict):
        article_dict = article
    else:
        raise ValueError("Expected a dataclass instance or dict")

    return json.dumps(article_dict, indent=4).encode("utf-8")


def dict_to_article(record: dict) -> Article:
    filtered_record = {
        key: record[key] for key in Article.__annotations__.keys() if key in record
    }
    return Article(**filtered_record)
