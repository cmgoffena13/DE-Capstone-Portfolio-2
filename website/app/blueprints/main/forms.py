from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class TickerForm(FlaskForm):
    tickers = StringField("Enter Stock Tickers", validators=[DataRequired()])


class NewsForm(FlaskForm):
    news = StringField("Enter News Search Term", validators=[DataRequired()])