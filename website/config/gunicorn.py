# -*- coding: utf-8 -*-

workers = 1
bind = "0.0.0.0:8001"
accesslog = "-"
access_log_format = (
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" in %(D)sµs'
)

# https://docs.gunicorn.org/en/stable/settings.html#logging
