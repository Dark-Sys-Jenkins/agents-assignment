import pyttsx3
import time
from pathlib import Path

class TextToSpeech:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', 150) # Adjust speed: higher is faster

    def speak(self, text):
        if not text: 
            return
        
        # Print what we are about to say for debugging
        print(f"🗣️ Speaking: {text}")
        
        try:
            self.engine.say(text)
            self.engine.runAndWait()
        except RuntimeError:
            pass

if __name__ == "__main__":
    tts = TextToSpeech()
    filepath = Path(__file__).parent / "easy_logging_status.txt"
    last_spoken_text = ""

    print(f"Monitoring {filepath}...")

    while True:
        try:
            if filepath.exists():
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()

                if lines:
                    raw_line = lines[-1].strip()

                    # Only proceed if the line has changed
                    if raw_line != last_spoken_text and raw_line:
                        
                        # Logic: Split by '|' and take the LAST item [-1]
                        parts = raw_line.split("|")
                        message = parts[-1].strip()

                        # Check for exit condition BEFORE speaking
                        if "exiting forcefully" in message.lower():
                            print("Exit signal received.")
                            tts.speak("Exiting forcefully")
                            break
                        
                        # Speak the message
                        tts.speak(message)
                        
                        # Update memory so we don't repeat it
                        last_spoken_text = raw_line
            
            # Check every 0.5 seconds
            time.sleep(0.5)

        except KeyboardInterrupt:
            print("\nStopping...")
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(1)