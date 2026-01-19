"""
Console Test Agent - No External APIs Required
Tests intelligent interruption logic directly in terminal

Run with: python console_test_agent.py
"""

import asyncio
import sys
from typing import Set
from dataclasses import dataclass

# Color codes for terminal output
class Color:
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    CYAN = '\033[96m'
    MAGENTA = '\033[95m'
    END = '\033[0m'
    BOLD = '\033[1m'


@dataclass
class Config:
    """Interruption configuration"""
    PASSIVE_WORDS: Set[str] = None
    INTERRUPT_WORDS: Set[str] = None
    
    def __post_init__(self):
        if self.PASSIVE_WORDS is None:
            self.PASSIVE_WORDS = {
                'yeah', 'ok', 'okay', 'hmm', 'uh-huh', 'right',
                'aha', 'mhm', 'yep', 'yup', 'mm-hmm', 'uhuh'
            }
        if self.INTERRUPT_WORDS is None:
            self.INTERRUPT_WORDS = {
                'wait', 'stop', 'no', 'hold', 'pause', 'but'
            }


class ConsoleAgent:
    """Simple console-based agent for testing interruption logic"""
    
    def __init__(self, config: Config):
        self.config = config
        self.is_speaking = False
        self.speech_task = None
        
    def should_ignore(self, text: str) -> bool:
        """
        Determine if input should be ignored
        
        Returns True if should IGNORE (agent continues)
        Returns False if should PROCESS (agent stops/responds)
        """
        
        if not self.is_speaking:
            return False  # Process all input when silent
        
        words = set(text.lower().strip().split())
        
        # Check for interrupt words
        if words & self.config.INTERRUPT_WORDS:
            return False  # Don't ignore - process interruption
        
        # Check if all words are passive
        non_empty = [w for w in words if w]
        if all(w in self.config.PASSIVE_WORDS for w in non_empty):
            return True  # Ignore - passive acknowledgement
        
        return False  # Mixed/new content - process
    
    async def speak(self, text: str):
        """Simulate agent speaking"""
        self.is_speaking = True
        
        print(f"\n{Color.BLUE}{Color.BOLD}🤖 Agent:{Color.END} {text}")
        
        # Simulate speech with word-by-word output
        words = text.split()
        for i, word in enumerate(words):
            if not self.is_speaking:  # Check if interrupted
                print(f"{Color.RED}[INTERRUPTED]{Color.END}")
                break
            
            print(f"{Color.CYAN}{word}{Color.END}", end=' ', flush=True)
            await asyncio.sleep(0.3)  # Simulate speaking pace
        
        print()  # New line
        self.is_speaking = False
        print(f"{Color.GREEN}🔇 Agent finished speaking{Color.END}")
    
    def stop_speaking(self):
        """Stop current speech"""
        if self.is_speaking:
            print(f"\n{Color.RED}⛔ Stopping agent speech{Color.END}")
            self.is_speaking = False
    
    async def handle_input(self, user_input: str):
        """Handle user input with intelligent filtering"""
        
        print(f"\n{Color.YELLOW}📝 User input: '{user_input}'{Color.END}")
        print(f"   Agent speaking: {self.is_speaking}")
        
        if self.should_ignore(user_input):
            print(f"{Color.MAGENTA}⏭️  IGNORED{Color.END} - Passive acknowledgement while speaking")
            return
        
        if self.is_speaking:
            print(f"{Color.RED}⛔ INTERRUPT{Color.END} - Stopping agent")
            self.stop_speaking()
            await asyncio.sleep(0.5)  # Brief pause
        
        # Generate and speak response
        response = self.generate_response(user_input)
        await self.speak(response)
    
    def generate_response(self, text: str) -> str:
        """Generate simple responses"""
        text_lower = text.lower()
        
        if any(w in text_lower for w in ['hello', 'hi', 'hey']):
            return "Hello! How can I help you today?"
        
        elif 'ai' in text_lower or 'artificial intelligence' in text_lower:
            return "Artificial intelligence is a fascinating field. It involves creating computer systems that can perform tasks requiring human intelligence such as learning, reasoning, problem-solving, perception, and language understanding. Modern AI uses techniques like machine learning and neural networks to process vast amounts of data."
        
        elif 'space' in text_lower or 'universe' in text_lower:
            return "The universe is incredibly vast and mysterious. It contains billions of galaxies, each with billions of stars. Our own Milky Way galaxy is just one among countless others. Scientists estimate the observable universe is about 93 billion light-years in diameter, and it continues to expand."
        
        elif 'ocean' in text_lower:
            return "The ocean is a vast and largely unexplored frontier. It covers more than 70 percent of Earth's surface and contains about 97 percent of all water on our planet. Ocean ecosystems are incredibly diverse, ranging from coral reefs teeming with life to the deep sea where mysterious creatures survive in total darkness."
        
        else:
            return "That's an interesting topic! Let me provide you with some information about that. There are several important aspects to consider, and I'll walk you through them step by step to give you a comprehensive understanding."


async def run_test_scenario(agent: ConsoleAgent, scenario_name: str, user_inputs: list, delays: list):
    """Run a specific test scenario"""
    
    print(f"\n{'='*60}")
    print(f"{Color.BOLD}{scenario_name}{Color.END}")
    print(f"{'='*60}")
    
    for user_input, delay in zip(user_inputs, delays):
        await asyncio.sleep(delay)
        await agent.handle_input(user_input)


async def run_automated_tests():
    """Run automated test scenarios"""
    
    config = Config()
    agent = ConsoleAgent(config)
    
    print(f"\n{Color.BOLD}🧪 Running Automated Test Scenarios{Color.END}\n")
    
    # Scenario 1: Long Explanation with Passive Acknowledgements
    await run_test_scenario(
        agent,
        "Scenario 1: Long Explanation with Passive Acknowledgements",
        [
            "Tell me about artificial intelligence",
            "yeah",
            "ok",
            "hmm"
        ],
        [0, 2, 1, 1]  # Delays between inputs
    )
    
    # Scenario 2: Passive Affirmation When Silent
    await run_test_scenario(
        agent,
        "Scenario 2: Passive Affirmation When Silent",
        [
            "Hello",
            "yeah"  # After agent finishes
        ],
        [0, 5]
    )
    
    # Scenario 3: Active Correction
    await run_test_scenario(
        agent,
        "Scenario 3: Active Correction",
        [
            "Tell me about space",
            "wait stop"
        ],
        [0, 2]
    )
    
    # Scenario 4: Mixed Input
    await run_test_scenario(
        agent,
        "Scenario 4: Mixed Input",
        [
            "Explain the ocean",
            "yeah but wait"
        ],
        [0, 2]
    )
    
    print(f"\n{Color.GREEN}{Color.BOLD}✅ All test scenarios completed!{Color.END}\n")


async def interactive_mode():
    """Run in interactive mode"""
    
    config = Config()
    agent = ConsoleAgent(config)
    
    print(f"\n{Color.BOLD}{'='*60}")
    print("🎙️  Interactive Console Agent - No External APIs")
    print(f"{'='*60}{Color.END}")
    print(f"\n{Color.CYAN}Instructions:{Color.END}")
    print("  - Type your message and press Enter")
    print("  - Try saying 'yeah' or 'ok' while agent is speaking")
    print("  - Try saying 'wait' or 'stop' to interrupt")
    print("  - Type 'test' to run automated scenarios")
    print("  - Type 'quit' to exit")
    print(f"\n{Color.YELLOW}Passive words:{Color.END} {', '.join(sorted(config.PASSIVE_WORDS))}")
    print(f"{Color.RED}Interrupt words:{Color.END} {', '.join(sorted(config.INTERRUPT_WORDS))}")
    print()
    
    # Initial greeting
    await agent.speak("Hello! I'm an intelligent voice assistant. Ask me anything, and notice how I handle your acknowledgements!")
    
    while True:
        try:
            user_input = input(f"\n{Color.GREEN}You: {Color.END}").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print(f"\n{Color.CYAN}Goodbye!{Color.END}\n")
                break
            
            if user_input.lower() == 'test':
                await run_automated_tests()
                continue
            
            await agent.handle_input(user_input)
            
        except KeyboardInterrupt:
            print(f"\n\n{Color.CYAN}Goodbye!{Color.END}\n")
            break
        except Exception as e:
            print(f"{Color.RED}Error: {e}{Color.END}")


async def main():
    """Main entry point"""
    
    if len(sys.argv) > 1 and sys.argv[1] == 'test':
        await run_automated_tests()
    else:
        await interactive_mode()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nExiting...")
