# processing_unit/emotion_classifier.py
import ollama

class EmotionClassifier:
    def __init__(self, model_name: str = "mistral:7b"):
        self.model_name = model_name
        self.system_prompt =  """Classify the following command into exactly ONE category:

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

    def classify(self, text: str) -> str:
        full_prompt = f"{self.system_prompt}\n\nCommand: \"{text}\"\Category:"

        response = ollama.generate(
            model=self.model_name,
            prompt=full_prompt,
            options={'temperature': 0.1}
        )

        result = response['response'].strip().lower()
        print(result)

        # Validate result
        valid_categories = ['happy', 'curious', 'concerned', 'scared', 'acknowledge']
        if result not in valid_categories:
            print("defaulting to acknowledge")
            return 'acknowledge'  # Default fallback

        return result
   
   
def main():
    # Test the classifier response with input commands
    print("R2-D2 Emotion Classifier Test")
    print("Type 'quit' to exit\n")

    classifier = EmotionClassifier()

    while True:
        user_input = input("Enter command: ")
        if user_input.lower() == 'quit':
            break
            
        emotion = classifier.classify(user_input)
        print(f"Classification: {emotion}\n")

if __name__ == "__main__":
   main()