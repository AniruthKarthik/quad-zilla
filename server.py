from fastapi import FastAPI

# CORS - cross origin resource sharing
from fastapi.middleware.cors import CORSMiddleware

# gives typed models to parse and validitate JSON.
from pydantic import BaseModel

from chat import ask_bot

# init the app
app = FastAPI()

# Allow frontend to call backend (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # later, replace "*" with your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request body schema
class Message(BaseModel):
    text: str

@app.post("/chat")
async def chat_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging

    response : str = ask_bot(message.text) 

    # return {"reply": "hi"}  # always return "hi" for now
    return {"reply" : response}
