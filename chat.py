# pip install -qU langchain-google-genai to call the model

from langgraph.prebuilt import create_react_agent
from langchain_google_genai import ChatGoogleGenerativeAI

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

# You'll need to get a Google AI Studio API key and set it as an environment variable
# export GOOGLE_API_KEY="YOUR_API_KEY"
llm = ChatGoogleGenerativeAI(model="gemini-1.5-pro-latest")

agent = create_react_agent(
    model=llm,
    tools=[get_weather],
    prompt="You are a helpful assistant"
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
print(result)