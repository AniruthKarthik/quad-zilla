from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
    return {"reply": "hi"}  # always return "hi" for now
