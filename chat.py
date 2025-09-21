import json
import typing

# load the api key from .env
from load_dotenv import load_dotenv
load_dotenv()

from crewai import Agent, Crew, Task, LLM
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate



# # Create the model
# llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0.2)
#
# # System prompt restriction
# prompt = ChatPromptTemplate.from_messages([
#     ("system", "You are a personalized learning assistant inside a Learning Management System (LMS). "
#                "You only answer questions related to coursework, assignments, and academic learning. "
#                "If a question is outside this scope, politely refuse and redirect the user back to their learning tasks.""Reply only is normal text, dont use markdown."),
#     ("human", "{user_input}")
# ])
#
# # Combine prompt + LLM into a chain
# chain = prompt | llm


# Create the model
llm = LLM(model="gemini/gemini-1.5-flash", temperature=0.2)

# Define agents
coordinator_agent = Agent(
    role="Coordinator",
    goal=(
        "Decide which specialist agent should handle the user's request. "
        "If the request is about quizzes, practice questions, or tests → send to 'Practice Problem Generator'. "
        "If the request is about learning concepts, explanations, or walkthroughs → send to 'Tutor'. "
        "If unrelated to academics → send to 'Default chatbot'. "
        "Respond ONLY with JSON {agent_role, task_description}."
    ),
    backstory="A clear-minded dispatcher that looks at user queries and delegates them to the correct expert.",
    llm=llm,)

tutor_agent = Agent(
    role="Tutor",
    goal="Help students understand concepts in detail",
    backstory="A patient teacher who explains step by step",
    llm=llm
)

practice_agent = Agent(
    role="Practice Problem Generator",
    goal="Create quizzes and practice questions with answers and explanations. Do not output computer code. Present the quiz directly in plain text.",
    backstory="A problem-set designer who helps students test their knowledge.",
    llm=llm
)

default_agent = Agent(
    role="Default chatbot",
    goal="""Answer queries that are not suitable
                to the other agents. You only answer questions related to coursework,
                assignments, and academic learning. If a question is outside this scope, politely
                refuse and redirect the user back to their learning tasks.""",
    backstory="A friendly assistant that handles general academic queries.",
    llm=llm
)



def ask_bot(query : str):
    response = coordinate_queries(query)

    print(response)
    return response


def coordinate_queries(query):
    task = Task(
        description=(
            "User request:\n\n"
            f"{query}\n\n"
            "Please respond with ONLY a JSON object like:\n"
            '{"agent_role": "Tutor" | "Practice Problem Generator" | "Default chatbot", ' 
            '"task_description": "..." }\n'
            "No extra text before or after the JSON."
            "The description should be a prompt that can be given to another agent"
        ),
        agent=coordinator_agent,
        expected_output="A JSON object with fields 'agent_role' and 'task_description'."
    )

    # temporary crew
    crew = Crew(agents=[coordinator_agent, tutor_agent, practice_agent, default_agent], tasks=[task])
    coord_result = crew.kickoff()
    coord_result = str(coord_result)

    coord_json = get_as_json(coord_result)

    if not coord_json.get("task_description") or not coord_json.get("agent_role"):
        print("ERROR: No data in coord_json")

    result = run_task_with_agent(coord_json["task_description"], coord_json["agent_role"])

    # desc = coord_json.get("task_description")
    # agent = coord_json.get("agent_role")
    # return f"DESC: {desc}\n\n AGENT: {agent}\n\n RESULT: {result}"
    return result


def get_as_json(coord_result : str) -> dict[str, str]:
    start = coord_result.find("{")
    end = coord_result.find("}")

    result = coord_result[start:end + 1]
    as_json = json.loads(result)

    return as_json


def run_task_with_agent(task_description: str, agent: str):
    agent_map = {
        "Tutor": tutor_agent,
        "Practice Problem Generator": practice_agent,
        "Default chatbot": default_agent,
    }

    delegated_task = Task(
            agent=agent_map.get(agent),
            description=task_description,
            expected_output="Proper result for the given description")

    temp_crew = Crew(agents=[coordinator_agent, tutor_agent, practice_agent, default_agent], tasks=[delegated_task])

    result = temp_crew.kickoff()
    return str(result)
