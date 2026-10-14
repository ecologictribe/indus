import os

class Config:
    BASE_DIR = os.path.abspath(os.path.dirname(__file__))
    DB_PATH = os.path.join(BASE_DIR, 'db', 'industrial_estates.db')
    SECRET_KEY = os.environ.get('SECRET_KEY', 'industrial-estates-secret-key-2026')
    DEBUG = True
    ITEMS_PER_PAGE = 25
