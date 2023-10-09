import base64
from fastapi import FastAPI, UploadFile, Form, Depends, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
from src.agent.simple import process_user_response
from langchain.schema import BaseMessage

from src.processing.resume import process_resume_and_jd
from src.processing.tts import do_text_to_speech
from bark import SAMPLE_RATE
from IPython.display import Audio
# import whisper
from bark import preload_models

# Preload AI models
preload_models(True,True,True,True,True,True,True,False)
# stt_model = whisper.load_model("small")

app = FastAPI()

from pydantic import BaseModel

class AIResponse(BaseModel):
    response: str


@app.post("/process-resume", response_model=AIResponse)
async def process_resume(resume: UploadFile = Form(...), jd: UploadFile = None):
    try:
        ai_reply = process_resume_and_jd(resume.file, jd.file if jd else None)
        return {"response": ai_reply}
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=400)



@app.post("/process-response", response_model=AIResponse)
async def user_response(response_audio: UploadFile = Form(...), chat_messages: list[BaseMessage] = Depends(lambda: [])):
    try:
        ai_reply = process_user_response(response_audio,chat_messages)
        ai_audio_obj = do_text_to_speech(ai_reply)
        binary_audio_data = ai_audio_obj.data
        ai_response_base64 = base64.b64encode(binary_audio_data).decode("utf-8")
        return {"response": ai_response_base64}
    except Exception as e:
        raise HTTPException(detail=str(e), status_code=400)
