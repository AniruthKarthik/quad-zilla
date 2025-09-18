import google.generativeai as genai

genai.configure(api_key="AIzaSyA4R0fK8vpOalvykeZCq59oMq1mvtr0o34")
model = genai.GenerativeModel(
            "models/gemini-1.5-flash", 
            system_instruction = (
                "You are a personalized learning assistant inside a Learning Management System (LMS). "
                "You only answer questions related to coursework, assignments, and academic learning. "
                "If a question is outside this scope, politely refuse and redirect the user back to their learning tasks."
    ))

def ask_bot(prompt : str) -> str:
    response = model.generate_content(prompt)
    print(response.text)

    return response.text
