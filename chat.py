import os

from load_dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

# genai.configure(api_key="AIzaSyA4R0fK8vpOalvykeZCq59oMq1mvtr0o34")
# model = genai.GenerativeModel(
#             "models/gemini-1.5-flash",
#             system_instruction = (
#                 "You are a personalized learning assistant inside a Learning Management System (LMS). "
#                 "You only answer questions related to coursework, assignments, and academic learning. "
#                 "If a question is outside this scope, politely refuse and redirect the user back to their learning tasks."
#     ))

# Setup Gemini through LangChain

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)

# System prompt restriction
prompt = ChatPromptTemplate.from_messages([
    ("system", "You are a personalized learning assistant inside a Learning Management System (LMS). "
               "You only answer questions related to coursework, assignments, and academic learning. "
               "If a question is outside this scope, politely refuse and redirect the user back to their learning tasks." "Reply only is normal text, dont use markdown."),
    ("human", "{user_input}")
])

# Combine prompt + LLM into a chain
chain = prompt | llm


def ask_bot(prompt : str) -> str:
    response = chain.invoke({"user_input": prompt})
    print(response.content)

    return response.content
