import os
import json
import random
import google.generativeai as genai
import asyncio
from subjects_data import SUBJECT_RESOURCES, GENERAL_STUDY_TIPS, MOTIVATIONAL_QUOTES, get_subject_info, get_study_tip_for_subject, get_resources_for_subject
from fuzzywuzzy import fuzz
from nltk.stem import WordNetLemmatizer
import nltk
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Download NLTK data (if not already downloaded)
def download_nltk_data():
    try:
        nltk.data.find('corpora/wordnet')
    except LookupError:
        logger.info("Downloading NLTK wordnet data...")
        nltk.download('wordnet')
    
    try:
        nltk.data.find('tokenizers/punkt')
    except LookupError:
        logger.info("Downloading NLTK punkt data...")
        nltk.download('punkt')

# Download NLTK data on import
download_nltk_data()

class ChatBot:
    def __init__(self):
        try:
            # Configure Gemini API
            api_key = os.environ.get("GEMINI_API_KEY")
            if not api_key:
                raise ValueError("GEMINI_API_KEY environment variable not found")
            
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel('gemini-pro')
            
            # Initialize components
            self.lemmatizer = WordNetLemmatizer()
            self.intents = self._load_intents("intents.json")
            self.words = []
            self.classes = []
            self.documents = []
            self._preprocess_intents()
            
            logger.info("ChatBot initialized successfully")
            
        except Exception as e:
            logger.error(f"Error initializing ChatBot: {e}")
            raise

    def _load_intents(self, file_path):
        """Load intents from JSON file with error handling"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return json.load(file)
        except FileNotFoundError:
            logger.warning(f"Intents file {file_path} not found. Using fallback intents.")
            return self._get_fallback_intents()
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing intents JSON: {e}")
            return self._get_fallback_intents()

    def _get_fallback_intents(self):
        """Provide fallback intents if intents.json is not available"""
        return [
            {
                "intent": "greeting",
                "patterns": ["hello", "hi", "hey", "good morning", "good afternoon"],
                "responses": ["Hello! I'm here to help you with your studies!", 
                            "Hi there! Ready to learn something new?"]
            },
            {
                "intent": "goodbye",
                "patterns": ["bye", "goodbye", "see you later", "quit", "exit"],
                "responses": ["Goodbye! Happy studying!", "See you later! Keep up the good work!"]
            },
            {
                "intent": "study_tip",
                "patterns": ["study tip", "how to study", "study advice", "study better"],
                "responses": ["Here's a study tip: "]
            },
            {
                "intent": "ask_subject",
                "patterns": ["help with", "learn about", "study", "subject"],
                "responses": ["I can help you with that subject! "]
            },
            {
                "intent": "motivation",
                "patterns": ["motivate me", "motivation", "encourage", "inspiration"],
                "responses": ["You've got this! "]
            }
        ]

    def _preprocess_intents(self):
        """Preprocess intents for pattern matching"""
        try:
            for intent in self.intents:
                for pattern in intent['patterns']:
                    word_list = nltk.word_tokenize(pattern.lower())
                    self.words.extend(word_list)
                    self.documents.append((word_list, intent['intent']))
                    if intent['intent'] not in self.classes:
                        self.classes.append(intent['intent'])
            
            # Clean and sort words
            self.words = [self.lemmatizer.lemmatize(word.lower()) for word in self.words if word.isalpha()]
            self.words = sorted(list(set(self.words)))
            self.classes = sorted(list(set(self.classes)))
            
        except Exception as e:
            logger.error(f"Error preprocessing intents: {e}")

    def _clean_up_sentence(self, sentence):
        """Clean and tokenize input sentence"""
        try:
            sentence_words = nltk.word_tokenize(sentence.lower())
            sentence_words = [self.lemmatizer.lemmatize(word) for word in sentence_words if word.isalpha()]
            return sentence_words
        except Exception as e:
            logger.error(f"Error cleaning sentence: {e}")
            return []

    def _bag_of_words(self, sentence):
        """Convert sentence to bag of words representation"""
        sentence_words = self._clean_up_sentence(sentence)
        bag = [0] * len(self.words)
        for w in sentence_words:
            for i, word in enumerate(self.words):
                if word == w:
                    bag[i] = 1
        return bag

    def _predict_class(self, sentence):
        """Predict intent class using fuzzy matching"""
        try:
            results = []
            sentence_words = self._clean_up_sentence(sentence)
            
            for i, doc in enumerate(self.documents):
                doc_words = doc[0]
                intent_tag = doc[1]
                
                # Calculate similarity score
                max_score = 0
                for pattern_word in doc_words:
                    for input_word in sentence_words:
                        score = fuzz.ratio(pattern_word, input_word)
                        if score > max_score:
                            max_score = score
                
                # Check for exact word matches as well
                word_matches = len(set(doc_words) & set(sentence_words))
                if word_matches > 0:
                    max_score = max(max_score, (word_matches / len(doc_words)) * 100)
                
                # Threshold for matching (adjustable)
                if max_score > 60:
                    results.append({'intent': intent_tag, 'probability': max_score / 100.0})
            
            # Remove duplicates and sort by probability
            unique_results = {}
            for result in results:
                intent = result['intent']
                if intent not in unique_results or result['probability'] > unique_results[intent]['probability']:
                    unique_results[intent] = result
            
            results = list(unique_results.values())
            results.sort(key=lambda x: x['probability'], reverse=True)
            return results
            
        except Exception as e:
            logger.error(f"Error predicting class: {e}")
            return []

    def _get_response_from_intents(self, intents_list, intents_json, user_input):
        """Generate response based on predicted intent"""
        if not intents_list:
            return None

        try:
            tag = intents_list[0]['intent']
            
            for intent in intents_json:
                if intent['intent'] == tag:
                    # Handle specific intents with dynamic responses
                    if tag == "ask_subject":
                        return self._handle_subject_query(intent, user_input)
                    elif tag == "study_tip":
                        return self._handle_study_tip(intent, user_input)
                    elif tag == "motivation":
                        return self._handle_motivation(intent)
                    else:
                        return random.choice(intent['responses'])
            
        except Exception as e:
            logger.error(f"Error getting response from intents: {e}")
        
        return None

    def _handle_subject_query(self, intent, user_input):
        """Handle subject-related queries"""
        try:
            subject_keywords = ["math", "physics", "chemistry", "biology", "computer science", "english", "history"]
            found_subject = None
            
            for keyword in subject_keywords:
                if keyword in user_input.lower():
                    found_subject = keyword
                    break
            
            if found_subject:
                subject_info = get_subject_info(found_subject)
                if subject_info:
                    base_response = random.choice(intent['responses'])
                    topics = ', '.join(subject_info['topics'][:3])
                    return f"{base_response} For {found_subject}, I can help with topics like: {topics}. Would you like study tips or resources for {found_subject}?"
            
            return random.choice(intent['responses'])
            
        except Exception as e:
            logger.error(f"Error handling subject query: {e}")
            return "I can help you with various subjects! What would you like to learn about?"

    def _handle_study_tip(self, intent, user_input):
        """Handle study tip requests"""
        try:
            subject_keywords = ["math", "physics", "chemistry", "biology", "computer science", "english", "history"]
            found_subject = None
            
            for keyword in subject_keywords:
                if keyword in user_input.lower():
                    found_subject = keyword
                    break
            
            tip = get_study_tip_for_subject(found_subject if found_subject else "")
            base_response = random.choice(intent['responses'])
            return f"{base_response}Here's a tip: {tip}"
            
        except Exception as e:
            logger.error(f"Error handling study tip: {e}")
            return "Here's a general study tip: Take regular breaks and stay organized!"

    def _handle_motivation(self, intent):
        """Handle motivation requests"""
        try:
            base_response = random.choice(intent['responses'])
            quote = random.choice(MOTIVATIONAL_QUOTES)
            return f"{base_response}Here's some motivation: {quote}"
        except Exception as e:
            logger.error(f"Error handling motivation: {e}")
            return "You're doing great! Keep up the good work!"

    async def get_bot_response(self, user_input):
        """Get bot response for user input"""
        try:
            # Validate input
            if not user_input or not user_input.strip():
                return "I didn't receive any message. Please try again!"
            
            user_input = user_input.strip()
            
            # Check for quit commands
            if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                return "Goodbye! Happy studying!"
            
            # Try to get response from intents first
            intents_list = self._predict_class(user_input)
            response_from_intents = self._get_response_from_intents(intents_list, self.intents, user_input)
            
            if response_from_intents:
                logger.info(f"Intent-based response for: {user_input}")
                return response_from_intents
            
            # Fallback to Gemini API
            logger.info(f"Using Gemini API for: {user_input}")
            try:
                # Add context for study-related responses
                study_context = "You are StudyBot, a helpful study assistant. Please provide educational and study-related guidance. User question: "
                response = self.model.generate_content(study_context + user_input)
                return response.text
                
            except Exception as e:
                logger.error(f"Gemini API error: {e}")
                return "I'm sorry, I'm having trouble connecting to the AI service right now. Please try again later, or ask me about study tips, subjects, or motivation!"
        
        except Exception as e:
            logger.error(f"Error in get_bot_response: {e}")
            return "I'm sorry, something went wrong. Please try again!"

# Main function for testing
async def main():
    """Main function for testing the chatbot"""
    print("=" * 50)
    print("🎓 Welcome to StudyBot - Your Personal Study Assistant!")
    print("=" * 50)
    print("I can help you with study-related questions using AI.")
    print("\nType 'quit', 'exit', or 'bye' to end our session.")
    print("-" * 50)
    
    try:
        bot = ChatBot()
        
        while True:
            user_input = input("\nYou: ").strip()
            if not user_input:
                continue
                
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("StudyBot: Goodbye! Happy studying! 📚")
                break
            
            response = await bot.get_bot_response(user_input)
            print(f"StudyBot: {response}")
            
    except KeyboardInterrupt:
        print("\nStudyBot: Goodbye! Happy studying! 📚")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())