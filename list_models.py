import google.generativeai as genai

genai.configure(api_key="AIzaSyA4R0fK8vpOalvykeZCq59oMq1mvtr0o34")

for model in genai.list_models():
    print(model.name)
