import asyncio
import json
import os
from typing import List
import redis
import uvicorn
from fastapi import FastAPI, WebSocket, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi_utilities import repeat_every
from starlette.websockets import WebSocketDisconnect

from app.config.config import Configurations
from app.database.db import DatabaseConnector
from app.routers.filtering import filter_router
from app.routers.operators import operator_router
from app.routers.settings import settings_router
from app.routers.analytics import analytics_router
from app.routers.call import call_router
from app.routers.sendmail import email_router, send_reset_mail
from app.utils.auth import get_current_user
from app.routers.notification import notification_router
from app.utils.sentiment_analyzer import SentimentAnalyzer
from app.utils.mailer import send_mail

os.makedirs(Configurations.UPLOAD_FOLDER, exist_ok=True)

app = FastAPI(title="ICSMS Call Analyzer REST API", dependencies=[Depends(get_current_user)])

redis_client = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT"), decode_responses=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(call_router, tags=["Call Recordings"])
app.include_router(analytics_router, tags=["Call Analytics"])
app.include_router(settings_router, tags=["Call Settings"])
app.include_router(operator_router, tags=["Call Operators"])
app.include_router(filter_router, tags=["Call Filtering"])
app.include_router(email_router, tags=["Email Notifications"])
app.include_router(notification_router, tags=["Notifications"])

sentiment_analyzer = SentimentAnalyzer()
settings_db = DatabaseConnector("settings")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_message(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/notify")
async def analysis_result(websocket: WebSocket):
    await manager.connect(websocket)
    await manager.send_message("From WebSocket Server")
    print(websocket)
    try:
        while True:
            received_msg = await websocket.receive_text()
            print(received_msg)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(e)


async def redis_listener():
    pubsub = redis_client.pubsub()
    pubsub.subscribe("task_notifications")
    print("Redis channel subscribed")
    while True:
        try:
            # Get the message from redis channel
            message = pubsub.get_message(ignore_subscribe_messages=True)

            if message is not None:
                # Send the notification to all connected clients
                await manager.send_message("From Redis Server")
                print("Message received from redis channel")
        except Exception as e:
            print(f"Error in redis_listener: {e}")
        await asyncio.sleep(0.01)


@app.on_event("startup")
async def startup_event():
    asyncio.create_task(redis_listener())


@app.on_event("startup")
@repeat_every(seconds=Configurations.status_check_frequency, wait_first=True)
def check_overall_sentiment_score():
    print("Checking overall sentiment score")
    avg_score_data = sentiment_analyzer.get_overall_avg_sentiment()
    avg_score = avg_score_data.get("avg_score")
    action_result = settings_db.get_all_entities()
    settings_configuration = action_result.data[0]
    settings_configuration = json.loads(json.dumps(settings_configuration))
    print(settings_configuration)
    lower_threshold = settings_configuration.get("sentiment_lower_threshold")
    upper_threshold = settings_configuration.get("sentiment_upper_threshold")

    if avg_score < lower_threshold:
        if settings_configuration.get('is_email_alerts_enabled'):
            print("Ok")
            receptions = settings_configuration.get("alert_email_receptions")
            subject = "Negative Overall Sentiment Score Detected"
            body = (f"Overall call analytics sentiment score has gone below the threshold: {lower_threshold}. "
                       f"It has been recorded as {avg_score}. Note that the above sentiment score is "
                   f"based on the data with last month.")
            mail = {"subject": subject, "body": body, "to": receptions}
            send_mail(mail)

    if avg_score > upper_threshold:
        if settings_configuration.get('is_email_alerts_enabled'):
            receptions = settings_configuration.get("alert_email_receptions")
            subject = "Positive Overall Sentiment Score Detected"
            body = (f"Overall call analytics sentiment score has gone above the threshold: {upper_threshold}. "
                    f"It has been recorded as {avg_score}. Note that the above sentiment score is "
                    f"based on the data with last month.")
            print("Ok")
            mail = {"subject": subject, "body": body, "to": receptions}
            send_mail(mail)


if __name__ == '__main__':
    uvicorn.run(app, port=8080)
