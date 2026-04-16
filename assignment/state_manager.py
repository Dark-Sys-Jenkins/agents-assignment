# state_manager.py

class StateManager:
    def __init__(self):
        self.is_agent_speaking = False

    def update_agent_state(self, state):
        if state == "speaking":
            self.is_agent_speaking = True
        else:
            self.is_agent_speaking = False