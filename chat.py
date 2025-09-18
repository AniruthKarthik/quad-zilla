import google.generativeai as genai

genai.configure(api_key="AIzaSyA4R0fK8vpOalvykeZCq59oMq1mvtr0o34")
model = genai.GenerativeModel("models/gemini-1.5-flash")

def ask_bot(prompt : str) -> str:
    response = model.generate_content(prompt)
    print(response.text)

    return response.text
