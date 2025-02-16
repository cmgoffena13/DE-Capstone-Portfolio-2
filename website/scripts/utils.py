import json
import random
import time
from dataclasses import asdict, dataclass

import requests
from marshmallow import ValidationError
from marshmallow_dataclass import class_schema


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


EquityAggSchema = class_schema(EquityAgg)


def equity_agg_to_json(equity_agg: EquityAgg):
    equity_agg_dict = asdict(equity_agg)
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


ArticleSchema = class_schema(Article)


def article_to_json(article: Article):
    article_dict = asdict(article)
    return json.dumps(article_dict, indent=4).encode("utf-8")


def dict_to_article(record: dict) -> Article:
    filtered_record = {
        key: record[key] for key in Article.__annotations__.keys() if key in record
    }
    return Article(**filtered_record)
