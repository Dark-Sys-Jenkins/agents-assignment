from livekit.agents.tokenize.basic import split_words
import re

filler_words = {
    "yeah","ya","yep","ok","okay","hmm","uh","um","right","mm","mmhmm","sure","alright","yea","yah","yup"
}

def is_filler(text):
    if not text:
        return True
    text_norm = re.sub(r"[^\w\s'-]", "", text.lower()).strip()
    words = [w[0] for w in split_words(text_norm, split_character=True)]
    meaningful = [w for w in words if w not in filler_words]
    return len(meaningful) == 0

samples = ['hmm', 'yeah', 'ok', 'okay', 'yeah go on', 'ok, go ahead', 'umm', 'mmhmm']
for s in samples:
    print(repr(s), '->', is_filler(s))
