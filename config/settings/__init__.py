# config/settings/__init__.py
import os

ENV = os.environ.get("DJANGO_ENV", "local")

if ENV == "production":
    from .production import *
else:
    from .local import *
