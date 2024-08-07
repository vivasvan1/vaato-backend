import logging
import traceback
from langchain.schema import SystemMessage
from src.utils.audio import convert_audio_to_base64
from src.agent.simple import process_user_response
from src.history.ChatMessageHistory import ChatMessageHistoryWithJSON
from src.processing.resume import calculate_questions, process_resume_and_jd
from src.processing.tts import do_text_to_speech
from fastapi import APIRouter, Body, FastAPI, UploadFile, Form, File, HTTPException
from pydantic import BaseModel
from typing import List


class AIResponse(BaseModel):
    response: str
    history: str


class QuestionsResponse(BaseModel):
    questions: List[str]


router = APIRouter()


@router.post(
    "/interview/questions",
    response_model=QuestionsResponse,
    tags=["Interview"],
    description="Get questions for the interview",
)
async def get_questions(
    resume: UploadFile = None,
    resumeText: str = Body(default=None),
    jd: UploadFile = None,
    jdText: str = Body(default=None),
    questions: str = Body(default=None),
):
    try:
        question_text = calculate_questions(
            resume.file if resume else None,
            jd.file if jd else None,
            resumeText,
            jdText,
            questions,
            [],
            True,
        )
        return {"questions": question_text.split("\n")}
    except Exception as e:
        raise HTTPException(detail=str(e.with_traceback()), status_code=400)


@router.post(
    "/interview/start",
    response_model=AIResponse,
    tags=["Interview"],
    description="Process the uploaded resume (optionally a job description) and produce AI response",
)
async def process_resume(
    resume: UploadFile = None,
    resumeText: str = Body(default=None),
    jd: UploadFile = None,
    jdText: str = Body(default=None),
    questions: str = Body(default=None),
    questions_list: List[str] = Body(default=[]),
    is_dynamic: bool = Body(default=True),
    voice: str = Body(default="echo"),
    language: str = Body(default="en")  # Added language parameter
):
    try:
        ai_reply, question_text, system_message = process_resume_and_jd(
            resume.file if resume else None,
            jd.file if jd else None,
            resumeText,
            jdText,
            questions,
            questions_list[0].split(",") if len(questions_list) else questions_list,
            is_dynamic,
        )
        history = ChatMessageHistoryWithJSON()
        history.add_message(SystemMessage(content=system_message))
        history.add_ai_message(ai_reply)

        # ai_response_base64 = convert_audio_to_base64(do_text_to_speech(ai_reply , voice=voice))

        # # save ai_response_base64 to file
        # with open(f'./public/first_messages/ai_first_reply_{voice}.wav', 'wb') as f:
        #     f.write(ai_response_base64.encode('ascii'))

        with open(f"./public/first_messages/ai_first_reply_{voice}_{language}.wav", "rb") as f:
            ai_response_base64 = f.read().decode("ascii")

        return {"response": ai_response_base64, "history": history.to_json()}

    except Exception as e:
        raise HTTPException(detail=str(e.with_traceback()), status_code=400)


@router.post(
    "/interview/next",
    response_model=AIResponse,
    tags=["Interview"],
    description="Process user's audio response and compute AI response",
)
async def user_response(
    response_audio: UploadFile = File(...),
    chat_messages: str = Form(...),
    voice: str = Body(default="alloy"),
    language: str = Body(default="en")  # Added language parameter
):
    try:
        logging.info("Received request for /interview/next")

        audio_bytes = await response_audio.read()

        # Check if audio_bytes is not empty
        if not audio_bytes:
            raise ValueError("No audio data found in the uploaded file")

        # convert chat_messages_string to list of AI, Human, System Messages
        history = ChatMessageHistoryWithJSON()
        history.from_json(chat_messages)

        ai_reply = process_user_response(audio_bytes, history)
        if not ai_reply:
            raise ValueError("AI reply is empty or null")

        ai_response_base64 = convert_audio_to_base64(
            do_text_to_speech(ai_reply, voice=voice,language=language)
        )
        if not ai_response_base64:
            raise ValueError("Failed to convert AI reply to base64 encoded audio")
        return {"response": ai_response_base64, "history": history.to_json()}

    except Exception as e:
        print(traceback.format_exc())
        logging.error(f"Error in user_response: {e}")
        raise HTTPException(detail=str(e), status_code=400)
