# Real-Time Stock Prices & News

This project utilizes Polygon's live stream and The Guardian's API to showcase real-time stock prices and news to watch for causation and signals in regards to day trading. 

[![build](https://github.com/cmgoffena13/DE-Capstone-Portfolio-2/actions/workflows/build.yml/badge.svg)](https://github.com/cmgoffena13/DE-Capstone-Portfolio-2/actions/workflows/build.yml)
![linesofcode](https://aschey.tech/tokei/github/cmgoffena13/DE-Capstone-Portfolio-2?category=code)

## Technologies Used
 ![Docker](https://img.shields.io/badge/-Docker-2496ED?style=flat&logoColor=white&logo=docker)
 ![Kafka](https://img.shields.io/badge/-Kafka-231F20?style=flat&logoColor=white&logo=apachekafka)
 ![Python](https://img.shields.io/badge/-Python-0077B5?style=flat&logoColor=white&logo=python)
 ![Flask](https://img.shields.io/badge/-Flask-000000?style=flat&logoColor=white&logo=flask) 
 ![Jinja](https://img.shields.io/badge/-Jinja-B41717?style=flat&logoColor=white&logo=jinja) 
 ![HTML](https://img.shields.io/badge/-HTML-E34F26?style=flat&logoColor=white&logo=html5) 
 ![Bootstrap](https://img.shields.io/badge/-Bootstrap-7952B3?style=flat&logoColor=white&logo=bootstrap) 
 ![Gunicorn](https://img.shields.io/badge/-Gunicorn-499848?style=flat&logoColor=white&logo=gunicorn)
![Git](https://img.shields.io/badge/-Git-F05032?style=flat&logoColor=white&logo=git)

## Design
![Design](website/app/static/README/design.png "Design")

## Table of Contents
1. [Introduction](#Introduction)
2. [Technology Choices](#Technology-Choices)
3. [Initial Data Investigations - Polygon Websocket](#Initial-Data-Investigations---Polygon-Websocket)
4. [Initial Data Investigations - The Guardian API](#Initial-Data-Investigations---The-Guardian-API)
5. [Website](#Website)
6. [Threading](#Threading)

## Introduction
This portfolio project is designed to showcase my ability to learn new technologies in regards to streaming. Every technology chosen in this project I had limited knowledge in. Each section is commentary on the project that includes my learnings along the way. Enjoy!

## Technology Choices
From a skillset perspective I am proficient in SQL and Python, which led me to choose these tools:
 - **Python**: easiest way to access Polygon's real-time websocket and The Guardian's API to get the data and send it to Kafka as a buffer
 - **Kafka**: a buffer to collect the results of the streams as a temporary storage. This is the de-facto tool for real-time message brokers. Checked out RabbitMQ but Kafka is better for real-time.
 - **Flink**: the de-facto tool for streaming with minimal latency. I had already worked with Spark, so I wanted to expand my skillset here.
 - **Iceberg**: Iceberg was created for streaming, gracefully handling appends. Works great with open source.
 - **Flask**: I am proficient in Flask web development and I wanted a web page so that I could easily adjust the stream inputs
 - **Grafana**: Free dashboard tool designed for real-time data. I had already used Prometheus before, so it made sense to gain proficiency in Grafana since they work so well together.
 - **Docker**: great way to re-produce environments and easily create a network using docker-compose

## Initial Data Investigations - Polygon Websocket

## Initial Data Investigations - The Guardian API

## Website
I decided early on that I wanted to create a web page to easily change the polygon and guardian query inputs. I ended up with a simple flask home page.
![Website](website/app/static/README/stock_tracker.PNG "Website")

## Threading
One of the main issues I ran into while using the flask home page is when submitting a form, the websocket held the main python thread, which never ended up reloading the page. I ended up with a simple solution to create a background thread for the websocket to have the web page load properly after a form submission.
```python
    def start_websocket(self, ws):
        def run_ws():
            with self.app.app_context():
                current_app.logger.debug("Starting Stream...")
            ws.run(handle_msg=self._handle_msg)

        threading.Thread(target=run_ws).start()
        with self.app.app_context():
            current_app.logger.debug("Stream Started")
```