from fastapi import FastAPI

# CORS - cross origin resource sharing
from fastapi.middleware.cors import CORSMiddleware

# gives typed models to parse and validitate JSON.
from pydantic import BaseModel

from chat import coordinate_queries, ask_search, ask_tutor, ask_practice

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
    response : dict = coordinate_queries(message.text)

    # return {"reply": "hi"}  # always return "hi" for now
    return response


@app.post("/search")
async def search_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging
    response : str = ask_search(message.text)

    # return {"reply": "hi"}  # always return "hi" for now
    return {"reply" : response}


@app.post("/practice")
async def practice_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging
    response : str = ask_practice(message.text)

    # return {"reply": "hi"}  # always return "hi" for now
    return {"reply" : response}


@app.post("/tutor")
async def tutor_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging
    response : str = ask_tutor(message.text)

    # return {"reply": "hi"}  # always return "hi" for now
    return {"reply" : response}
