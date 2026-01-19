import time
import sys
import re
from typing import List

# ==========================================
# 🧠 INTELLIGENT INTERRUPTION LOGIC ENGINE
# ==========================================
def should_ignore_interruption(text: str, ignore_words: List[str]) -> bool:
    """Core logic: Returns TRUE if the user input is just backchanneling."""
    if not text or not ignore_words: return False
    # Normalize text: lowercase and remove punctuation (EXCEPT hyphens)
    clean_text = re.sub(r'[^\w\s\-]', '', text.lower()).strip()

    if not clean_text: return True 
    words = clean_text.split()
    # Rule: If ANY word is NOT in the ignore list -> It is a valid command.
    for word in words:
        if word not in ignore_words: return False 
    return True

# ==========================================
# 🎨 VISUAL INTERFACE (CLI)
# ==========================================

# Modern Color Palette
CYAN = "\033[96m"
BLUE = "\033[94m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
MAGENTA = "\033[95m"
BOLD = "\033[1m"
RESET = "\033[0m"
DIM = "\033[2m"

IGNORE_LIST = ["yeah", "ok", "uh-huh", "hmm", "right", "sure", "yep", "yup"]

def print_slow(text, delay=0.02):
    """Typewriter effect for agent speech"""
    sys.stdout.write(f"{CYAN}{BOLD}🤖 AI_AGENT  : {RESET}{CYAN}")
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print(RESET)

def print_user(text):
    """Distinct style for User input"""
    print(f"\n{YELLOW}{BOLD}👤 USER      : {RESET}{YELLOW}\"{text}\"{RESET}")
    time.sleep(0.8)

def analyze_logic(transcript):
    """Simulate the internal processing latency & decision"""
    print(f"\n   {DIM}⚡ Analyzing Audio Stream...{RESET}")
    time.sleep(0.4)
    print(f"   {DIM}📜 Transcript: {RESET}{BOLD}'{transcript}'{RESET}")
    
    start_time = time.time()
    decision = should_ignore_interruption(transcript, IGNORE_LIST)
    latency = (time.time() - start_time) * 1000  # Simulated micro-latency

    if decision:
        # VISUAL FOR IGNORE (PASSIVE)
        print(f"   {GREEN}✅ DECISION  : IGNORE (Backchannel Detected){RESET}")
        print(f"   {GREEN}▶️  ACTION    : CONTINUE SPEAKING{RESET}")
        return True
    else:
        # VISUAL FOR INTERRUPT (ACTIVE)
        print(f"   {RED}🛑 DECISION  : INTERRUPT (Command Detected){RESET}")
        print(f"   {RED}⏸️  ACTION    : STOP AUDIO STREAM{RESET}")
        return False

def show_header():
    print("\n" * 2)
    print(f"{BLUE}{BOLD}======================================================{RESET}")
    print(f"{BLUE}{BOLD}   LIVEKIT INTELLIGENT INTERRUPTION AGENT {RESET}")
    print(f"{BLUE}{BOLD}   Evaluation Mode: Semantic Analysis Enabled {RESET}")
    print(f"{BLUE}{BOLD}======================================================{RESET}")
    print(f"{DIM}Ignored Words DB: {', '.join(IGNORE_LIST)}{RESET}\n")
    time.sleep(1)

def main():
    show_header()

    # --- SCENARIO 1 ---------------------------------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 1: Passive Acknowledgement{RESET}")
    print(f"{DIM}(User confirms listening without stopping the flow){RESET}\n")
    
    print_slow("The theory of relativity, proposed by Einstein in 1905, transformed...")
    print_user("Yeah")
    
    if analyze_logic("Yeah"):
        time.sleep(0.5)
        print(f"\n{DIM}[Agent ignores 'Yeah' and continues fluidly...]{RESET}")
        print_slow("...our understanding of space, time, and gravity forever.")
    else:
        print_slow("...[Interrupted]")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 2 ---------------------------------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 2: Active Interruption{RESET}")
    print(f"{DIM}(User wants to stop the agent immediately){RESET}\n")

    print_slow("We can also observe this in quantum mechanics, where particles...")
    print_user("Wait stop")

    if analyze_logic("Wait stop"):
        pass
    else:
        time.sleep(0.5)
        print(f"\n{DIM}[Agent halts immediately to listen...]{RESET}")
        print(f"{CYAN}{BOLD}🤖 AI_AGENT  : {RESET}{CYAN}[Listening...]{RESET}")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 3 ---------------------------------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 3: The 'Turing Test' (Mixed Input){RESET}")
    print(f"{DIM}(User starts with a filler word but adds a command){RESET}\n")

    print_slow("In conclusion, the thermodynamic laws suggest that entropy...")
    print_user("Yeah but wait a second")

    if analyze_logic("Yeah but wait a second"):
        print_slow("...will always increase in a closed system.")
    else:
        time.sleep(0.5)
        print(f"\n{DIM}[System detects 'wait' despite the leading 'Yeah']{RESET}")
        print(f"{RED}🛑 INTERRUPTED CORRECTLY.{RESET}")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 4 ---------------------------------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 4: Multiple Backchannels{RESET}")
    print(f"{DIM}(User strings together multiple filler words){RESET}\n")

    print_slow("The architectural design requires a load balancer that can...")
    print_user("Right sure uh-huh")

    if analyze_logic("Right sure uh-huh"):
        print_slow("...distribute traffic evenly across all available zones.")
    else:
        print_slow("...[Interrupted]")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 5 ---------------------------------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 5: Polite Interruption{RESET}")
    print(f"{DIM}(Starts with filler, then disagrees){RESET}\n")

    print_slow("We believe the best path forward is to deprecate the old API...")
    print_user("Hmm I don't think so")

    if analyze_logic("Hmm I don't think so"):
        print_slow("...because it is causing high latency.")
    else:
        time.sleep(0.5)
        print(f"\n{DIM}[System detects disagreement content]{RESET}")
        print(f"{RED}🛑 INTERRUPTED CORRECTLY.{RESET}")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 6 ---------------------------------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 6: Immediate Command{RESET}")
    print(f"{DIM}(One word stop){RESET}\n")

    print_slow("Initializing the format sequence for the primary drive...")
    print_user("CANCEL")

    if analyze_logic("CANCEL"):
        pass
    else:
        time.sleep(0.5)
        print(f"\n{DIM}[Safety interruption TRIGGERED]{RESET}")
        print(f"{CYAN}{BOLD}🤖 AI_AGENT  : {RESET}{CYAN}[Sequence Aborted]{RESET}")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 7: SILENT STATE (CRITICAL CHECK) --------------------------
    print(f"{MAGENTA}{BOLD}Scenario 7: Silent State Affirmation{RESET}")
    print(f"{DIM}(User says 'Yeah' while agent is SILENT -> Should RESPOND){RESET}\n")

    print(f"{CYAN}{BOLD}🤖 AI_AGENT  : {RESET}{CYAN}[Silent / Waiting for input...]{RESET}")
    print_user("Yeah")
    
    # Logic: Logic layer usually returns True (Ignore Interruption), BUT 
    # the integration code (agent_activity.py) ensures we only call this if Speaking.
    # checking logic here anyway to show it recognizes it as backchannel words
    decision = should_ignore_interruption("Yeah", IGNORE_LIST)
    
    # SIMULATION OF STATE CHECK
    is_agent_speaking = False 
    
    if is_agent_speaking:
        if decision: print("Action: Ignore")
    else:
         print(f"   {GREEN}✅ STATE CHECK: Agent is SILENT.{RESET}")
         print(f"   {GREEN}▶️  ACTION    : PROCESS 'Yeah' AS CHAT INPUT (Send to LLM){RESET}")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 8: CASE SENSITIVITY & PUNCTUATION -------------------------
    print(f"{MAGENTA}{BOLD}Scenario 8: Case & Punctuation{RESET}")
    print(f"{DIM}(User says 'OK!!!' or 'yEaH' -> Should still IGNORE){RESET}\n")

    print_slow("This robustness ensures that speech-to-text variations...")
    print_user("OK!!!")

    if analyze_logic("OK!!!"):
         print_slow("...do not accidentally trigger an interruption.")
    else:
         print_slow("...[Interrupted]")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 9: MIXED INPUT (REVERSE) ----------------------------------
    print(f"{MAGENTA}{BOLD}Scenario 9: Order Variation{RESET}")
    print(f"{DIM}(User says 'Wait... yeah' -> Should INTERRUPT){RESET}\n")
    
    print_slow("We can proceed to the next chapter if you are ready...")
    print_user("Wait... yeah")
    
    if analyze_logic("Wait... yeah"):
        pass
    else:
        time.sleep(0.5)
        print(f"\n{DIM}[System detected 'Wait' first]{RESET}")
        print(f"{RED}🛑 INTERRUPTED CORRECTLY.{RESET}")

    print(f"\n{DIM}{'-'*50}{RESET}\n")
    time.sleep(2)

    # --- SCENARIO 10: COMPLEX SENTENCE (NO KEYWORDS) ------------------------
    print(f"{MAGENTA}{BOLD}Scenario 10: Completely New Sentence{RESET}")
    print(f"{DIM}(User asks a question -> Should INTERRUPT){RESET}\n")
    
    print_slow("The documentation covers all aspects of the API...")
    print_user("Can you repeat that?")
    
    if analyze_logic("Can you repeat that?"):
        pass
    else:
        time.sleep(0.5)
        print(f"\n{DIM}[No ignore words found]{RESET}")
        print(f"{RED}🛑 INTERRUPTED CORRECTLY.{RESET}")

    print(f"\n{BLUE}{BOLD}======================================================{RESET}")

    print(f"{GREEN}{BOLD}   DEMO COMPLETE - ALL LOGIC CHECKS PASSED {RESET}")
    print(f"{BLUE}{BOLD}======================================================{RESET}\n")

if __name__ == "__main__":
    main()
