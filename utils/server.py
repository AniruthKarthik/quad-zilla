import os
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from cbot import ChatBot # Import the ChatBot from cbot.py
import asyncio

# Load environment variables from .env
load_dotenv()


# Initialize FastAPI
app = FastAPI()
templates = Jinja2Templates(directory=".")

# Allow cross-origin requests from frontend (adjust in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Replace "*" with your frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the ChatBot from cbot.py
bot = ChatBot()

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("interface.html", {"request": request})

@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "").strip()
    if not user_input:
        return {"response": "Please type a message."}
    
    response = await bot.get_bot_response(user_input)
    return {"response": response}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

