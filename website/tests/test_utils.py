import json
from datetime import datetime, timezone

import pytest
from marshmallow import ValidationError
from scripts.utils import (
    Article,
    EquityAgg,
    article_to_json,
    dict_to_article,
    equity_agg_to_json,
)


def valid_article_data():
    return {
        "id": "1",
        "type": "news",
        "sectionId": "world",
        "sectionName": "World News",
        "webPublicationDate": "2024-02-18T12:00:00Z",
        "webTitle": "Test Article",
        "webUrl": "http://example.com",
        "apiUrl": "http://api.example.com",
        "isHosted": False,
        "pillarId": "pillar/news",
        "pillarName": "News",
        "search": "example",
    }


def test_article_creation_valid():
    data = valid_article_data()
    article = Article(**data)
    for key, value in data.items():
        assert getattr(article, key) == value


def test_article_creation_data_type_invalid():
    data = valid_article_data()
    data["webPublicationDate"] = 1
    with pytest.raises(ValidationError):
        Article(**data)


def test_article_creation_null_invalid():
    data = valid_article_data()
    data["webPublicationDate"] = None
    with pytest.raises(ValidationError):
        Article(**data)


def test_article_to_influx_json():
    data = valid_article_data()
    article = Article(**data)
    influx = article.to_influx_json()

    assert influx["measurement"] == "news_articles"
    assert influx["tags"] == {"search": data["search"]}

    dt = datetime.strptime(data["webPublicationDate"], "%Y-%m-%dT%H:%M:%SZ").replace(
        tzinfo=timezone.utc
    )
    expected_time = int(dt.timestamp() * 1_000_000)
    assert influx["time-field"] == expected_time

    for key, value in data.items():
        # Because we converted to time-field
        if key != "webPublicationDate":
            assert key in influx
            assert influx[key] == value


def test_article_to_json_with_dataclass():
    data = valid_article_data()
    article = Article(**data)
    json_bytes = article_to_json(article)
    loaded = json.loads(json_bytes.decode("utf-8"))
    assert loaded == data


def test_article_to_json_with_dict():
    data = valid_article_data()
    json_bytes = article_to_json(data)
    loaded = json.loads(json_bytes.decode("utf-8"))
    assert loaded == data


def test_article_to_json_invalid_input():
    with pytest.raises(ValueError):
        article_to_json(123)


def test_dict_to_article_valid():
    data = valid_article_data()
    data_extra = data.copy()
    data_extra["extra_field"] = "this should be ignored"
    article = dict_to_article(data_extra)
    for key in Article.__annotations__.keys():
        assert getattr(article, key) == data[key]


def test_dict_to_article_missing_field():
    data = valid_article_data()
    data.pop("id")
    with pytest.raises(TypeError):
        dict_to_article(data)


def valid_equity_agg_data():
    return {
        "event_type": "trade",
        "symbol": "AAPL",
        "volume": 1000,
        "accumulated_volume": 5000,
        "official_open_price": 150.0,
        "vwap": 151.0,
        "open": 150.0,
        "close": 152.0,
        "high": 153.0,
        "low": 149.0,
        "aggregate_vwap": 151.5,
        "average_size": 100,
        "start_timestamp": 1672531200,
        "end_timestamp": 1672534800,
        "otc": None,
    }


def test_equity_agg_valid_creation():
    data = valid_equity_agg_data()
    eq = EquityAgg(**data)
    for key, value in data.items():
        assert getattr(eq, key) == value


def test_equity_agg_data_type_invalid_creation():
    data = valid_equity_agg_data()
    data["volume"] = "not an int"
    with pytest.raises(ValidationError):
        EquityAgg(**data)


def test_equity_agg_null_invalid_creation():
    data = valid_equity_agg_data()
    data["volume"] = None
    with pytest.raises(ValidationError):
        EquityAgg(**data)


def test_equity_agg_to_influx_json():
    data = valid_equity_agg_data()
    eq = EquityAgg(**data)
    influx = eq.to_influx_json()

    assert influx["measurement"] == "stock_prices"
    assert influx["tags"] == {"symbol": data["symbol"]}

    expected_time = int(data["end_timestamp"] * 1_000_000_000)
    assert influx["time-field"] == expected_time

    for key, value in data.items():
        if key != "end_timestamp":
            assert key in influx
            assert influx[key] == value


def test_equity_agg_to_json_with_dataclass():
    data = valid_equity_agg_data()
    eq = EquityAgg(**data)
    json_bytes = equity_agg_to_json(eq)

    loaded = json.loads(json_bytes.decode("utf-8"))
    assert loaded == data


def test_equity_agg_to_json_with_dict():
    data = valid_equity_agg_data()
    json_bytes = equity_agg_to_json(data)
    loaded = json.loads(json_bytes.decode("utf-8"))
    assert loaded == data


def test_equity_agg_to_json_invalid_input():
    with pytest.raises(ValueError):
        equity_agg_to_json(123)
