from fastapi import FastAPI

# CORS - cross origin resource sharing
from fastapi.middleware.cors import CORSMiddleware

# gives typed models to parse and validitate JSON.
from pydantic import BaseModel

from chat import coordinate_queries, run_task_with_agent

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
    print("User said:", message.text)

    # Get the agent and task from the coordinator
    coord_response = coordinate_queries(message.text)

    # Check if the default chatbot should be used
    if coord_response.get("agent_role") == "Default chatbot":
        # If so, run the task and return the reply in the format the frontend expects
        reply = run_task_with_agent(coord_response["task_description"], "Default chatbot")
        return {"reply": reply, "agent_role": "Default chatbot"}

    # For any other agent, return the coordinator's response to trigger redirection
    return coord_response


@app.post("/search")
async def search_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging
    response : str = run_task_with_agent(str(message.text), "Search")

    return {"reply" : response}


@app.post("/practice")
async def practice_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging
    response : str = run_task_with_agent(str(message.text), "Practice Problem Generator")

    return {"reply" : response}


@app.post("/tutor")
async def tutor_endpoint(message: Message):
    print("User said:", message.text)  # just for debugging
    response : str = run_task_with_agent(str(message.text), "Tutor")

    return {"reply" : response}
