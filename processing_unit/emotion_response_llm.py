# processing_unit/emotion_classifier.py
import argparse
import io
import ollama

class EmotionClassifier:
    """Local emotion classifier using Ollama"""
    def __init__(self, model_name: str = "mistral:7b"):
        self.model_name = model_name
        self.system_prompt = """Classify the following command into exactly ONE category:
            - happy
            - curious
            - concerned
            - scared
            - acknowledge
            Rules:
            - Output only the category word (happy, curious, concerned, scared, acknowledge).
            - No explanation or extra text.
            - If unsure, pick the closest category.
            Examples:
            "Hello" → happy
            "What's that?" → curious
            "Help me" → concerned
            "Danger!" → scared
            "Status" → acknowledge
            """
        self.valid_categories = ['happy', 'curious', 'concerned', 'scared', 'acknowledge']

    def classify(self, text: str) -> str:
        full_prompt = f"{self.system_prompt}\n\nCommand: \"{text}\"\nCategory:"
        response = ollama.generate(
            model=self.model_name,
            prompt=full_prompt,
            options={'temperature': 0.1}
        )
        result = response['response'].strip().lower()
        print(result)
        
        if result not in self.valid_categories:
            print("defaulting to acknowledge")
            return 'acknowledge'
        return result


class EmotionClassifier_API:
    """Cloud emotion classifier using Groq API"""
    def __init__(self, api_key: str = None):
        """
        Initialize Groq client.
        If api_key is None, uses GROQ_API_KEY environment variable.
        """
        from groq import Groq
        from dotenv import load_dotenv
        load_dotenv()  # Loads .env into environment variables
        print("Loaded env variables")
        
        self.client = Groq(api_key=api_key)
        self.system_prompt = """Classify the following command into exactly ONE category:
            - happy
            - curious
            - concerned
            - scared
            - acknowledge
            Rules:
            - Output only the category word (happy, curious, concerned, scared, acknowledge).
            - No explanation or extra text.
            - If unsure, pick the closest category.
            Examples:
            "Hello" → happy
            "What's that?" → curious
            "Help me" → concerned
            "Danger!" → scared
            "Status" → acknowledge
            """
        self.valid_categories = ['happy', 'curious', 'concerned', 'scared', 'acknowledge']

    def transcribe(self, audio_bytes: bytes) -> str:
        """Convert audio bytes to text using Groq Whisper"""
        audio_file = io.BytesIO(audio_bytes)
        audio_file.name = "audio.wav"
        
        transcription = self.client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=audio_file
        )
        return transcription.text

    def classify(self, text: str) -> str:
        """Classify text into emotion category using Groq LLM"""
        response = self.client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.1
        )
        result = response.choices[0].message.content.strip().lower()
        print(result)
        
        if result not in self.valid_categories:
            print("defaulting to acknowledge")
            return 'acknowledge'
        return result

    def process_audio(self, audio_bytes: bytes) -> tuple[str, str]:
        """
        Full pipeline: audio -> text -> emotion
        Returns: (transcribed_text, emotion)
        """
        text = self.transcribe(audio_bytes)
        print(f"Heard: {text}")
        emotion = self.classify(text)
        return text, emotion


def main():
    parser = argparse.ArgumentParser(description="R2-D2 Emotion Classifier Test")
    parser.add_argument('--local', action='store_true', help="Use local GPU (Ollama) instead of Groq API")
    args = parser.parse_args()

    if args.local:
        print("R2-D2 Emotion Classifier Test (Local Ollama)")
        classifier = EmotionClassifier()
    else:
        print("R2-D2 Emotion Classifier Test (Groq API)")
        print("Using GROQ_API_KEY environment variable")
        classifier = EmotionClassifier_API()

    print("Type 'quit' to exit\n")

    while True:
        user_input = input("Enter command: ")
        if user_input.lower() == 'quit':
            break

        emotion = classifier.classify(user_input)
        print(f"Classification: {emotion}\n")


if __name__ == "__main__":
    main()