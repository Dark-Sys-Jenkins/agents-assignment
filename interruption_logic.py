import re

class InterruptionLogic:

    BACKCHANNEL_WORDS = {
        "yeah", "yea", "ok", "okay",
        "uh", "uhh", "hmm", "mhmm",
        "ok got it", "great", "good",
        "good idea", "sounds good", "cool"
    }

    INTERRUPT_WORDS = {

        "stop", "wait", "hold on", "pause",
        "fine stop", "stop it", "cut it out",
        "enough", "halt", "yeah stop", "no more",
        "thats enough", "leave it", "forget it", 
        "yeah wait", "yeah but wait", "hold up", 
        "just a second", "yeah but hold on"
    }

    @classmethod
    def normalize(cls, text: str) -> str:
        
        text = text.lower()
        text = re.sub(r"[^\w\s]", "", text)
        
        return text.strip()

    @classmethod
    def is_backchannel(cls, text: str) -> bool:
        
        return cls.normalize(text) in cls.BACKCHANNEL_WORDS

    @classmethod
    def is_interrupt(cls, text: str) -> bool:
        norm_text = cls.normalize(text)
        
        
        return any(word in norm_text for word in cls.INTERRUPT_WORDS)

    @classmethod
    def is_interruption_required(cls, transcript: str, agent_speaking: bool) -> bool:
        if not agent_speaking:
            return False
        return cls.is_interrupt(transcript)

if __name__ == "__main__":
    test_cases = [
        ("Stop right there!", True),
        ("Yeah, I see.", False),
        ("Hold on a second.", True),
        ("That's a good idea.", False),
        ("Pause the conversation.", True),
        ("Uh huh.", False),
        ("Yeah. but wait", True)
    ]

    print(f"{'Text':<30} | {'Expected':<8} | {'Result':<8} | {'Pass?'}")
    print("-" * 65)

    for text, expected in test_cases:
        result = InterruptionLogic.is_interruption_required(text, agent_speaking=True)
        status = "True" if result == expected else "False"
        print(f"'{text}':<30 | {str(expected):<8} | {str(result):<8} | {status}")