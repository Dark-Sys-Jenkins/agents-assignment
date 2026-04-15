from interrupt_handler.handler import InterruptionHandler

handler = InterruptionHandler()

print("=== DEMO ===")

handler.set_agent_state(True)
print("Speaking + yeah →", handler.handle_input("yeah"))
print("Speaking + stop →", handler.handle_input("stop"))

handler.set_agent_state(False)
print("Silent + yeah →", handler.handle_input("yeah"))