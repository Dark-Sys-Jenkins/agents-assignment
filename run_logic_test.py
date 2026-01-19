import sys
from livekit.agents.voice.interruption_logic import should_ignore_interruption

# Color codes for output
GREEN = "\033[92m"
RED = "\033[91m"
RESET = "\033[0m"

APP_IGNORE_LIST = ["yeah", "ok", "uh-huh", "hmm", "right"]

def run_test(name, result, expected):
    if result == expected:
        print(f"{GREEN}[PASS]{RESET} {name}")
        return True
    else:
        print(f"{RED}[FAIL]{RESET} {name}: Expected {expected}, got {result}")
        return False

def main():
    print("Running Interruption Logic Tests...")
    failures = 0

    # Basic Ignored Words
    if not run_test("Ignore 'Yeah'", should_ignore_interruption("Yeah", APP_IGNORE_LIST), True): failures += 1
    if not run_test("Ignore 'ok'", should_ignore_interruption("ok", APP_IGNORE_LIST), True): failures += 1
    
    # Commands (Not Ignored)
    if not run_test("Interrupt on 'Stop'", should_ignore_interruption("Stop", APP_IGNORE_LIST), False): failures += 1
    if not run_test("Interrupt on 'Wait'", should_ignore_interruption("Wait", APP_IGNORE_LIST), False): failures += 1
    
    # Compound Sentences
    if not run_test("Interrupt on 'Yeah wait'", should_ignore_interruption("Yeah wait", APP_IGNORE_LIST), False): failures += 1
    if not run_test("Interrupt on 'Ok but'", should_ignore_interruption("Ok but", ["yeah", "ok"]), False): failures += 1
    if not run_test("Ignore 'Yeah ok'", should_ignore_interruption("Yeah ok", APP_IGNORE_LIST), True): failures += 1
    
    # Edge Cases
    if not run_test("Ignore punctuation 'Yeah.'", should_ignore_interruption("Yeah.", APP_IGNORE_LIST), True): failures += 1
    if not run_test("Ignore case 'YEAH'", should_ignore_interruption("YEAH", APP_IGNORE_LIST), True): failures += 1
    
    if failures == 0:
        print(f"\n{GREEN}All tests passed!{RESET}")
        sys.exit(0)
    else:
        print(f"\n{RED}{failures} tests failed.{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
