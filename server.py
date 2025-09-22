from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse
# CORS - cross origin resource sharing
from fastapi.middleware.cors import CORSMiddleware
# gives typed models to parse and validate JSON.
from pydantic import BaseModel

# Try importing chat functions, with fallback if they fail
try:
    from chat import coordinate_queries, run_task_with_agent
    CHAT_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import chat functions: {e}")
    CHAT_AVAILABLE = False

import uvicorn

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

# Mount static files (for serving HTML, CSS, JS, images)
app.mount("/static", StaticFiles(directory="ACM"), name="static")

# Define request body schema
class Message(BaseModel):
    text: str

# Root route - redirect to login page
@app.get("/")
async def root():
    return RedirectResponse(url="/static/login.html")

# Health check endpoint for load balancer
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "Service is running"}

# Alternative: serve login.html directly at root
# @app.get("/")
# async def root():
#     return FileResponse("ACM/login.html")

@app.post("/chat")
async def chat_endpoint(message: Message):
    if not CHAT_AVAILABLE:
        return {"reply": "Chat service temporarily unavailable", "agent_role": "Error"}
    
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
    if not CHAT_AVAILABLE:
        return {"reply": "Search service temporarily unavailable"}
    
    print("User said:", message.text)  # just for debugging
    response: str = run_task_with_agent(str(message.text), "Search")
    return {"reply": response}

@app.post("/practice")
async def practice_endpoint(message: Message):
    if not CHAT_AVAILABLE:
        return {"reply": "Practice service temporarily unavailable"}
    
    print("User said:", message.text)  # just for debugging
    response: str = run_task_with_agent(str(message.text), "Practice Problem Generator")
    return {"reply": response}

@app.post("/tutor")
async def tutor_endpoint(message: Message):
    if not CHAT_AVAILABLE:
        return {"reply": "Tutor service temporarily unavailable"}
    
    print("User said:", message.text)  # just for debugging
    response: str = run_task_with_agent(str(message.text), "Tutor")
    return {"reply": response}

# FastAPI server - remove this since we use uvicorn in Dockerfile CMD
# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)
