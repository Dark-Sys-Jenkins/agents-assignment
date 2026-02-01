# local_tts.py
import pyttsx3
import threading

class LocalTTS:
    def __init__(self):
        self.engine = pyttsx3.init()
        self.engine.setProperty("rate", 170)

        self.lock = threading.Lock()

    def _speak(self, text):
        with self.lock:
            self.engine.say(text)
            self.engine.runAndWait()

    def speak(self, text: str):
        t = threading.Thread(target=self._speak, args=(text,), daemon=True)
        t.start()
