from fastapi import APIRouter, BackgroundTasks, Depends

from app.utils.auth import get_current_user
from app.utils.mail_sender import send_mail
from app.models.action_result import ActionResult
from app.models.send_mail import MailObject

import logging

logging.basicConfig(level=logging.INFO)

email_router = APIRouter(dependencies=[Depends(get_current_user)])


@email_router.post("/send-reset-mail", response_model=ActionResult)
async def send_reset_mail(mails: MailObject, task:BackgroundTasks):
    data = mails.dict()
    task.add_task(send_mail, data)
    return ActionResult(success=True, message="Reset mail task added")
