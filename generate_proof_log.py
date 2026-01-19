import sys
import re
from typing import List

# ==========================================
# 🧠 RE-IMPLEMENTED LOGIC (For standalone verifiable testing)
# ==========================================
def should_ignore_interruption(text: str, ignore_words: List[str]) -> bool:
    if not text or not ignore_words: return False
    # Regex allows hyphens for "uh-huh"
    clean_text = re.sub(r'[^\w\s\-]', '', text.lower()).strip()
    if not clean_text: return True 
    words = clean_text.split()
    for word in words:
        if word not in ignore_words: return False 
    return True

IGNORE_LIST = ["yeah", "ok", "okay", "hmm", "uh-huh", "right", "sure", "yep", "yup", "gotcha", "aha", "mhmm"]

# ==========================================
# 🧪 MASSIVE TEST SUITE (50 Scenarios)
# ==========================================
# Format: (Transcript Input, Expected Action, Description)
# Action True = IGNORE (Backchannel)
# Action False = INTERRUPT (Command/Content)

scenarios = [
    # --- SIMPLE BACKCHANNELS (Should IGNORE) ---
    ("Yeah", True, "Basic backchannel"),
    ("ok", True, "Basic lowercase"),
    ("OKAY", True, "Case insensitive"),
    ("Uh-huh", True, "Hyphenated word"),
    ("Hmm", True, "Thinking sound"),
    ("Right", True, "Agreement"),
    ("Sure", True, "Agreement"),
    ("Yep", True, "Casual yes"),
    ("Yup", True, "Casual yes"),
    ("Gotcha", True, "Understanding"),
    ("Aha", True, "Realization"),
    ("Mhmm", True, "Murmur agreement"),
    
    # --- PUNCTUATION & FORMATTING (Should IGNORE) ---
    ("Yeah.", True, "Period"),
    ("Ok!!!", True, "Exclamation"),
    ("...hmm...", True, "Ellipsis"),
    ("Right?", True, "Question mark tone"),
    ("  Okay  ", True, "Whitespace trimming"),
    ("YeAH", True, "Mixed case"),
    
    # --- MULTIPLE BACKCHANNELS (Should IGNORE) ---
    ("Yeah ok", True, "Two backchannels"),
    ("Right sure", True, "Agreement combo"),
    ("Uh-huh okay", True, "Hyphen + word"),
    ("Hmm right yeah", True, "Triple combo"),
    ("Yep gotcha", True, "Casual combo"),
    
    # --- ACTIVE COMMANDS (Should INTERRUPT) ---
    ("Stop", False, "Direct stop"),
    ("Wait", False, "Direct wait"),
    ("Cancel", False, "Direct cancel"),
    ("No", False, "Disagreement"),
    ("Hold on", False, "Phrase command"),
    ("Pause", False, "Playback control"),
    ("Quit", False, "Exit command"),
    ("Silence", False, "Sound control"),
    
    # --- MIXED INTENT (The "Smart" Tests - Should INTERRUPT) ---
    ("Yeah but", False, "Agreement with objection"),
    ("Okay wait", False, "Backchannel + Command"),
    ("Sure stop", False, "Agreement + Stop"),
    ("Right... no", False, "Hesitant disagreement"),
    ("Hmm actually", False, "Thinking then correcting"),
    ("Uh-huh wait a sec", False, "Backchannel + Phrase"),
    ("Yeah I have a question", False, "Backchannel + Question"),
    ("Ok turn it off", False, "Backchannel + Action"),
    ("Right but... wrong", False, "Nuanced connection"),
    ("Yep hold on", False, "Casual + Command"),
    
    # --- CONTENT & QUESTIONS (Should INTERRUPT) ---
    ("I don't understand", False, "User confusion"),
    ("Can you repeat?", False, "Request for repetition"),
    ("What was that?", False, "Question"),
    ("Go back", False, "Navigation"),
    ("That is wrong", False, "Correction"),
    ("Change volume", False, "System command"),
    ("Who are you?", False, "Identity question"),
    ("Tell me more", False, "Engagement"),
    
    # --- EDGE CASES (Should INTERRUPT) ---
    ("Yeah...", True, "Trailing dots (Still Ignore)"), 
    ("Okay!!!!!", True, "Loud agreement (Still Ignore)"),
    ("Yeah NO", False, "Mixed case yelling (Interrupt)"),
    ("Um", False, "Filler NOT in list (Interrupts by default safe mode)"),
    ("Well", False, "Starter word (Interrupts)"),
]

def run_suite():
    print("================================================================")
    print(f"🕵️  MASSIVE INTERRUPTION LOGIC AUDIT ({len(scenarios)} Scenarios)")
    print("================================================================\n")
    
    passed = 0
    failed = 0
    
    log_file = open("comprehensive_test_log.txt", "w")
    log_file.write(f"TEST RUN TIMESTAMP: {sys.version}\n")
    log_file.write(f"TOTAL SCENARIOS: {len(scenarios)}\n")
    log_file.write("-" * 60 + "\n")
    log_file.write(f"{'TRANSCRIPT':<25} | {'EXPECTED':<10} | {'ACTUAL':<10} | {'RESULT'}\n")
    log_file.write("-" * 60 + "\n")

    for text, expected_ignore, desc in scenarios:
        # Run Logic
        should_ignore = should_ignore_interruption(text, IGNORE_LIST)
        
        # Determine Status
        status = "PASS" if should_ignore == expected_ignore else "FAIL"
        
        # Pretty Print to Console
        icon = "✅" if status == "PASS" else "❌"
        action = "IGNORE (Keep Talking)" if should_ignore else "INTERRUPT (Stop)"
        
        print(f"{icon} Input: '{text}'")
        print(f"   Desc:   {desc}")
        print(f"   Result: {action}")
        print("-" * 40)
        
        # Write to Log File
        log_file.write(f"{text:<25} | {'IGNORE' if expected_ignore else 'INT':<10} | {'IGNORE' if should_ignore else 'INT':<10} | {status}\n")

        if status == "PASS":
            passed += 1
        else:
            failed += 1

    # Final Summary
    print("\n================================================================")
    print(f"TEST SUMMARY: {passed} PASSED, {failed} FAILED")
    print("================================================================")
    
    log_file.write("-" * 60 + "\n")
    log_file.write(f"FINAL RESULT: {passed}/{len(scenarios)} PASSED\n")
    log_file.close()
    
    print(f"\n📂 Detailed log saved to: comprehensive_test_log.txt")

if __name__ == "__main__":
    run_suite()
