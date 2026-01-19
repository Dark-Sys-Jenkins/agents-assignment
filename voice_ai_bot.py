import speech_recognition as sr
import pyttsx3
from openai import OpenAI

# -------------------
# OpenAI setup
# -------------------
client = OpenAI()
MODEL_NAME = "gpt-4o-mini"

# -------------------
# Audio setup
# -------------------
recognizer = sr.Recognizer()
mic = sr.Microphone()
tts = pyttsx3.init()
tts.setProperty("rate", 170)

# -------------------
# Interruption Config
# -------------------
IGNORE_WORDS = {"yeah", "ok", "okay", "hmm", "right", "uh-huh"}
INTERRUPT_WORDS = {"stop", "wait", "cancel", "no", "pause"}

agent_speaking = False

print("🎤 Voice AI Bot Started (with smart interruption)")
print("Say something (say 'exit' to quit)\n")


# -------------------
# Interruption Logic
# -------------------
def should_interrupt(text: str, agent_speaking: bool) -> bool:
    text = text.lower().strip()
    words = set(text.split())

    # If agent is silent → always allow
    if not agent_speaking:
        return True

    # If any strong interrupt word present → interrupt
    if words & INTERRUPT_WORDS:
        return True

    # If only ignore words → ignore
    if words and words.issubset(IGNORE_WORDS):
        return False

    # Mixed or unknown input while speaking → interrupt
    return True


# -------------------
# Voice + AI functions
# -------------------
def speak(text):
    global agent_speaking
    agent_speaking = True
    print("\n🤖 Bot:", text)
    tts.say(text)
    tts.runAndWait()
    agent_speaking = False


def ask_ai(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content.strip()


# -------------------
# Main loop
# -------------------
while True:
    with mic as source:
        recognizer.adjust_for_ambient_noise(source, duration=0.5)
        print("🎧 Listening...")
        audio = recognizer.listen(source)

    try:
        text = recognizer.recognize_google(audio)
        print("🧑 You:", text)

        if text.lower() == "exit":
            print("👋 Bye!")
            break

        interrupt = should_interrupt(text, agent_speaking)

        if agent_speaking and not interrupt:
            print("⛔ Ignored soft input while agent speaking")
            continue

        answer = ask_ai(text)
        speak(answer)

    except sr.UnknownValueError:
        print("❌ Could not understand audio")
    except Exception as e:
        print("⚠️ Error:", e)

