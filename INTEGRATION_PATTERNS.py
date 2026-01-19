"""
LIVEKIT AGENT INTEGRATION PATTERNS

This file demonstrates how to integrate the InterruptionHandler into various
LiveKit agent patterns and architectures.
"""

import logging
from typing import Optional

# from interruption_handler import InterruptionHandler, InterruptionType, InterruptionConfig

logger = logging.getLogger(__name__)


# ============================================================================
# PATTERN 1: Simple Agent with Interruption Handling
# ============================================================================

class SimpleAgentWithInterruption:
    """
    Simplest integration pattern:
    - Initialize handler
    - Hook into start/stop speaking
    - Filter STT input
    """
    
    def __init__(self):
        """Initialize agent with interruption handler"""
        # from interruption_handler import InterruptionHandler
        # self.handler = InterruptionHandler()
        self.handler = None  # Placeholder
        self.current_response = None
    
    async def handle_user_input(self, transcript: str):
        """
        Process user input with interruption filtering
        
        Args:
            transcript: Speech-to-text transcript from user
        """
        # Check interruption type
        # interruption_type = self.handler.process_user_input(transcript)
        # 
        # if interruption_type == InterruptionType.IGNORE:
        #     logger.debug(f"Ignoring backchannel: {transcript}")
        #     return
        # 
        # elif interruption_type == InterruptionType.INTERRUPT:
        #     logger.warning(f"Interrupting with: {transcript}")
        #     await self.stop_response()
        # 
        # else:  # RESPOND
        #     logger.info(f"Processing response: {transcript}")
        #     await self.generate_response(transcript)
        pass
    
    async def start_speaking(self):
        """Agent starts generating/speaking"""
        # self.handler.set_agent_speaking(True)
        logger.info("Agent started speaking")
    
    async def stop_speaking(self):
        """Agent stops speaking"""
        # self.handler.set_agent_speaking(False)
        logger.info("Agent stopped speaking")
    
    async def generate_response(self, user_input: str):
        """Generate and send response"""
        logger.info(f"Generating response for: {user_input}")
        # Actual implementation here
    
    async def stop_response(self):
        """Stop current response"""
        logger.warning("Stopping current response")
        # Cancel generation/playback


# ============================================================================
# PATTERN 2: Async Event-Driven Agent
# ============================================================================

class AsyncEventAgent:
    """
    Event-driven pattern for agent with continuous event monitoring:
    - Separate event handlers for each lifecycle stage
    - Callback-based processing
    - Clean separation of concerns
    """
    
    def __init__(self):
        """Initialize event-driven agent"""
        # from interruption_handler import InterruptionHandler
        # self.handler = InterruptionHandler()
        self.handler = None  # Placeholder
        self.events = {
            'user_speech': [],
            'agent_start': [],
            'agent_stop': [],
            'interrupt': [],
        }
    
    def subscribe(self, event_type: str, callback):
        """Subscribe to events"""
        if event_type in self.events:
            self.events[event_type].append(callback)
    
    async def on_user_speech(self, transcript: str):
        """Handle user speech event"""
        # Process through interruption handler
        # interruption_type = self.handler.process_user_input(transcript)
        # 
        # if interruption_type == InterruptionType.INTERRUPT:
        #     await self._emit_event('interrupt', transcript)
        # elif interruption_type == InterruptionType.RESPOND:
        #     await self._emit_event('user_speech', transcript)
        # # IGNORE events are not emitted
        
        logger.info(f"User speech received: {transcript}")
    
    async def on_agent_start_speaking(self):
        """Handle agent start speaking event"""
        # self.handler.set_agent_speaking(True)
        # await self._emit_event('agent_start', None)
        logger.info("Agent started speaking")
    
    async def on_agent_stop_speaking(self):
        """Handle agent stop speaking event"""
        # self.handler.set_agent_speaking(False)
        # await self._emit_event('agent_stop', None)
        logger.info("Agent stopped speaking")
    
    async def _emit_event(self, event_type: str, data):
        """Emit event to all subscribers"""
        for callback in self.events.get(event_type, []):
            try:
                await callback(data)
            except Exception as e:
                logger.error(f"Error in event handler: {e}")


# ============================================================================
# PATTERN 3: Agent with State Machine
# ============================================================================

class StateMachineAgent:
    """
    State machine pattern for complex agent behavior:
    - Explicit states: IDLE, LISTENING, SPEAKING, PROCESSING
    - State transitions guarded by business logic
    - Interruption handling integrated into state machine
    """
    
    class State:
        IDLE = "IDLE"
        LISTENING = "LISTENING"
        SPEAKING = "SPEAKING"
        PROCESSING = "PROCESSING"
        INTERRUPTED = "INTERRUPTED"
    
    def __init__(self):
        """Initialize state machine agent"""
        # from interruption_handler import InterruptionHandler
        # self.handler = InterruptionHandler()
        # self.handler.register_interrupt_callback(self._on_interrupt)
        self.handler = None  # Placeholder
        self.state = self.State.IDLE
        self.history = []
    
    def _transition_to(self, new_state: str):
        """Transition to new state"""
        old_state = self.state
        self.state = new_state
        self.history.append({
            'from': old_state,
            'to': new_state,
        })
        logger.info(f"State transition: {old_state} -> {new_state}")
    
    async def on_user_speech(self, transcript: str):
        """Handle user speech based on current state"""
        # interruption_type = self.handler.process_user_input(transcript)
        # 
        # if interruption_type == InterruptionType.IGNORE:
        #     logger.debug(f"Ignoring in {self.state} state: {transcript}")
        #     return
        # 
        # if self.state == self.State.SPEAKING:
        #     if interruption_type == InterruptionType.INTERRUPT:
        #         self._transition_to(self.State.INTERRUPTED)
        #         await self._handle_interrupt(transcript)
        # 
        # elif self.state == self.State.IDLE or self.state == self.State.LISTENING:
        #     if interruption_type == InterruptionType.RESPOND:
        #         self._transition_to(self.State.PROCESSING)
        #         await self.process_input(transcript)
        
        logger.info(f"Processing in {self.state} state: {transcript}")
    
    async def _on_interrupt(self, transcript: str):
        """Interrupt callback"""
        logger.warning(f"Interrupt callback: {transcript}")
        self._transition_to(self.State.INTERRUPTED)
    
    async def process_input(self, transcript: str):
        """Process user input"""
        logger.info(f"Processing: {transcript}")
        self._transition_to(self.State.IDLE)
    
    async def _handle_interrupt(self, transcript: str):
        """Handle interruption"""
        logger.warning(f"Handling interrupt: {transcript}")
        self._transition_to(self.State.LISTENING)


# ============================================================================
# PATTERN 4: Multi-Agent System with Shared Handler
# ============================================================================

class SharedInterruptionHandlerPool:
    """
    Pool pattern for multiple agents sharing interruption handling:
    - Central configuration
    - Shared word lists
    - Per-agent state tracking
    - Useful for multi-room scenarios
    """
    
    def __init__(self, room_id: str):
        """
        Initialize shared handler pool
        
        Args:
            room_id: Room identifier
        """
        # from interruption_handler import InterruptionConfig, InterruptionHandler
        # 
        # # Shared configuration
        # self.config = InterruptionConfig()
        # self.room_id = room_id
        # self.agents = {}
        # self.handler_pool = {}
        
        self.config = None
        self.room_id = room_id
        self.agents = {}
        self.handler_pool = {}
        
        logger.info(f"Shared handler pool initialized for room: {room_id}")
    
    def create_agent_handler(self, agent_id: str):
        """Create handler for specific agent"""
        # handler = InterruptionHandler(self.config)
        # self.handler_pool[agent_id] = handler
        # logger.info(f"Created handler for agent: {agent_id}")
        # return handler
        pass
    
    def get_agent_handler(self, agent_id: str):
        """Get handler for specific agent"""
        return self.handler_pool.get(agent_id)


# ============================================================================
# PATTERN 5: Advanced: Interruption with Context
# ============================================================================

class ContextAwareInterruptionAgent:
    """
    Advanced pattern combining interruption handling with conversation context:
    - Tracks conversation history
    - Contextual word interpretation
    - Custom interrupt logic based on current topic
    - Learning from user behavior
    """
    
    def __init__(self):
        """Initialize context-aware agent"""
        # from interruption_handler import InterruptionHandler, InterruptionConfig
        # self.handler = InterruptionHandler()
        self.handler = None  # Placeholder
        self.conversation_context = []
        self.topic_stack = []
        self.custom_interrupts = {}
    
    def set_current_topic(self, topic: str):
        """Set current conversation topic"""
        self.topic_stack.append(topic)
        logger.info(f"Topic pushed: {topic}")
        self._update_context_aware_config()
    
    def pop_topic(self):
        """Pop from topic stack"""
        if self.topic_stack:
            topic = self.topic_stack.pop()
            logger.info(f"Topic popped: {topic}")
            self._update_context_aware_config()
    
    def _update_context_aware_config(self):
        """
        Update interruption config based on current context
        
        Example: Different interrupt words for different topics
        """
        current_topic = self.topic_stack[-1] if self.topic_stack else None
        
        if current_topic == "MEDICAL":
            # Medical context: "stop" is critical, "pause" might be synonym
            logger.info("Applied MEDICAL context configuration")
        
        elif current_topic == "CASUAL":
            # Casual context: more lenient, allow more interruptions
            logger.info("Applied CASUAL context configuration")
    
    async def process_with_context(self, transcript: str):
        """Process input considering conversation context"""
        # Store in history
        self.conversation_context.append({
            'text': transcript,
            'topic': self.topic_stack[-1] if self.topic_stack else 'GENERAL',
        })
        
        # Process through interruption handler
        # interruption_type = self.handler.process_user_input(transcript)
        # 
        # # Could apply additional context-aware logic here
        # if len(self.conversation_context) > 10:
        #     # Maybe adjust sensitivity based on conversation length
        #     pass
        
        logger.info(f"Context-aware processing: {transcript}")


# ============================================================================
# PATTERN 6: Testing Pattern with Mock Handler
# ============================================================================

class AgentWithMockInterruption:
    """
    Pattern for testing agents with interruption handling:
    - Mock interruption handler for testing
    - Predefined test scenarios
    - Assertion helpers
    """
    
    def __init__(self, use_mock: bool = False):
        """
        Initialize agent with optional mock
        
        Args:
            use_mock: Use mock handler for testing
        """
        if use_mock:
            self.handler = MockInterruptionHandler()
            logger.info("Using MOCK interruption handler")
        else:
            # from interruption_handler import InterruptionHandler
            # self.handler = InterruptionHandler()
            self.handler = None  # Placeholder
            logger.info("Using REAL interruption handler")
    
    async def test_scenario(self, scenario_name: str, inputs: list):
        """
        Run test scenario
        
        Args:
            scenario_name: Name of scenario
            inputs: List of (transcript, expected_action) tuples
        """
        logger.info(f"Running scenario: {scenario_name}")
        
        for transcript, expected in inputs:
            result = self.handler.process_user_input(transcript)
            # assert result == expected, f"Mismatch for {transcript}"
            logger.info(f"  ✓ {transcript} -> {result}")


class MockInterruptionHandler:
    """Mock interruption handler for testing"""
    
    def __init__(self):
        self.call_history = []
    
    def process_user_input(self, transcript: str):
        """Mock process_user_input"""
        self.call_history.append(transcript)
        # Return mock result based on transcript
        if "wait" in transcript.lower() or "stop" in transcript.lower():
            return "INTERRUPT"
        elif any(bc in transcript.lower() for bc in ["yeah", "ok", "hmm"]):
            return "IGNORE"  # In default state
        else:
            return "RESPOND"
    
    def set_agent_speaking(self, is_speaking: bool):
        """Mock set_agent_speaking"""
        self.call_history.append(f"set_speaking({is_speaking})")
    
    def get_call_history(self):
        """Get call history for assertions"""
        return self.call_history


# ============================================================================
# PATTERN 7: Production Deployment Pattern
# ============================================================================

class ProductionAgent:
    """
    Production-ready pattern with:
    - Proper error handling
    - Metrics/telemetry
    - Configuration management
    - Health checks
    """
    
    def __init__(self, config_dict: Optional[dict] = None):
        """Initialize production agent"""
        # from interruption_handler import InterruptionHandler, InterruptionConfig
        
        # Apply configuration
        if config_dict:
            # custom_config = InterruptionConfig(
            #     backchannel_words=set(config_dict.get('backchannel_words', [])),
            #     interrupt_commands=set(config_dict.get('interrupt_commands', [])),
            # )
            # self.handler = InterruptionHandler(custom_config)
            logger.info(f"Production agent with custom config loaded")
        else:
            # self.handler = InterruptionHandler()
            logger.info("Production agent with default config loaded")
        
        self.handler = None  # Placeholder
        self.metrics = {
            'total_inputs': 0,
            'ignored': 0,
            'interrupted': 0,
            'responded': 0,
            'errors': 0,
        }
    
    async def handle_input_with_metrics(self, transcript: str):
        """Handle input while tracking metrics"""
        try:
            self.metrics['total_inputs'] += 1
            
            # interruption_type = self.handler.process_user_input(transcript)
            # 
            # if interruption_type == InterruptionType.IGNORE:
            #     self.metrics['ignored'] += 1
            # elif interruption_type == InterruptionType.INTERRUPT:
            #     self.metrics['interrupted'] += 1
            # else:
            #     self.metrics['responded'] += 1
            
            logger.info(f"Input processed: {transcript}")
        
        except Exception as e:
            self.metrics['errors'] += 1
            logger.error(f"Error processing input: {e}")
    
    def get_health_status(self):
        """Get agent health status"""
        error_rate = (self.metrics['errors'] / max(1, self.metrics['total_inputs'])) * 100
        
        return {
            'status': 'HEALTHY' if error_rate < 1.0 else 'DEGRADED',
            'total_inputs': self.metrics['total_inputs'],
            'error_rate_percent': error_rate,
            'metrics': self.metrics,
        }


# ============================================================================
# PATTERN 8: Configuration Management
# ============================================================================

def create_agent_for_environment(env: str):
    """
    Factory function to create agent with environment-specific configuration
    
    Args:
        env: Environment name (development, staging, production)
    """
    configs = {
        'development': {
            'backchannel_words': ['yeah', 'ok', 'hmm'],
            'interrupt_commands': ['stop', 'wait'],
            'enabled': True,
            'case_insensitive': True,
        },
        'staging': {
            'backchannel_words': ['yeah', 'ok', 'hmm', 'uh-huh', 'right'],
            'interrupt_commands': ['stop', 'wait', 'hold', 'no'],
            'enabled': True,
            'case_insensitive': True,
        },
        'production': {
            'backchannel_words': [
                'yeah', 'yes', 'ok', 'okay', 'hmm', 'uh-huh',
                'right', 'aha', 'mm', 'ah', 'uh',
            ],
            'interrupt_commands': [
                'stop', 'wait', 'hold', 'no', 'halt',
                'hold on', 'hold up',
            ],
            'enabled': True,
            'case_insensitive': True,
        },
    }
    
    if env not in configs:
        logger.warning(f"Unknown environment: {env}, using production config")
        env = 'production'
    
    config = configs[env]
    logger.info(f"Creating agent for environment: {env}")
    logger.info(f"Config: {config}")
    
    # from interruption_handler import InterruptionConfig, InterruptionHandler
    # interrupt_config = InterruptionConfig(**config)
    # return InterruptionHandler(interrupt_config)
    
    return None  # Placeholder


# ============================================================================
# USAGE EXAMPLES
# ============================================================================

async def example_1_simple():
    """Example 1: Simple integration"""
    agent = SimpleAgentWithInterruption()
    await agent.start_speaking()
    await agent.handle_user_input("yeah")  # Will be ignored
    await agent.stop_speaking()
    await agent.handle_user_input("yeah")  # Will be processed


async def example_2_state_machine():
    """Example 2: State machine agent"""
    agent = StateMachineAgent()
    # Agent transitions through states based on interruption handling


async def example_3_production():
    """Example 3: Production deployment"""
    agent = ProductionAgent(config_dict={
        'backchannel_words': ['yeah', 'ok', 'hmm'],
        'interrupt_commands': ['stop', 'wait'],
    })
    
    await agent.handle_input_with_metrics("yeah")
    health = agent.get_health_status()
    logger.info(f"Health: {health}")


if __name__ == "__main__":
    print(__doc__)
    print("\nUse these patterns as templates for your agent implementation.")
    print("\nSee examples/interruption_handler_example.py for working example.")
