from pathlib import Path
from dotenv import load_dotenv
import os

load_dotenv()


class Configurations:
    UPLOAD_FOLDER = Path(".\data").resolve()
    SAVED_FOLDER = Path(".\mp3").resolve()
    sentiment_categories = ["Positive", "Negative", "Neutral"]
    aws_access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
    aws_secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    bucket_name = os.getenv("BUCKET_NAME")
    mongo_db_url = os.getenv("MONGO_DB_URL")
    aws_region = os.getenv("AWS_DEFAULT_REGION")
    celery_broker_url = os.getenv("CELERY_BROKER_URL")
    celery_result_backend = os.getenv("CELERY_RESULT_BACKEND")
    celery_config = os.getenv("CELERY_CONFIG")
    topics = ["Sales", "Payments", "Customer Inquiries", "Technical Support", "Order Tracking"]
