from livekit.agents.tokenize.basic import split_words

def check(text):
    words = [w[0].lower() for w in split_words(text.lower(), split_character=True)]
    print(f"'{text}' -> {words}")

check("yeah")
check("yeah.")
check("yeah!")
check("Yeah, wait")
check("stop")
check("Stop.")
