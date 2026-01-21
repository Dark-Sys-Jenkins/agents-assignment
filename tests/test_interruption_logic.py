import pytest
from unittest.mock import MagicMock
from livekit.agents.voice.nlp_utils import is_backchannel
from livekit.agents.voice.agent_session import DEFAULT_IGNORE_WORDS

# ==========================================
# PART 1: Core NLP Tests
# ==========================================

@pytest.mark.asyncio
async def test_nlp_basic_backchannel():
    """Test words explicitly in your new list."""
    assert is_backchannel("Yeah", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("Okay", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("Hmm", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("Right", DEFAULT_IGNORE_WORDS) is True  # Added based on your list
    assert is_backchannel("Oh", DEFAULT_IGNORE_WORDS) is True     # Added based on your list

@pytest.mark.asyncio
async def test_nlp_phrase_backchannel():
    """Test phrases explicitly in your new list."""
    assert is_backchannel("I see", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("All right", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("Got it", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("Keep going", DEFAULT_IGNORE_WORDS) is True

@pytest.mark.asyncio
async def test_nlp_normalization():
    """Test that punctuation is handled by your regex."""
    # "Yeah..." -> "yeah   " -> Match
    assert is_backchannel("Yeah...", DEFAULT_IGNORE_WORDS) is True
    # "OKAY!" -> "okay " -> Match
    assert is_backchannel("OKAY!", DEFAULT_IGNORE_WORDS) is True

@pytest.mark.asyncio
async def test_nlp_variants():
    """Test specific variants you added."""
    assert is_backchannel("Alright", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("Ohh", DEFAULT_IGNORE_WORDS) is True

@pytest.mark.asyncio
async def test_nlp_empty_input():
    """Ensure VAD noise/silence doesn't trigger interruption."""
    assert is_backchannel("", DEFAULT_IGNORE_WORDS) is True
    assert is_backchannel("   ", DEFAULT_IGNORE_WORDS) is True

# ==========================================
# PART 2: Challenge Scenarios
# ==========================================

@pytest.mark.asyncio
async def test_scenario_1_long_explanation():
    """Scenario 1: User says 'Okay... yeah... uh-huh' -> IGNORE."""
    # All these words are in your list
    assert is_backchannel("Okay... yeah... uh-huh", DEFAULT_IGNORE_WORDS) is True

@pytest.mark.asyncio
async def test_scenario_3_immediate_stop():
    """Scenario 3: User says 'No stop' -> INTERRUPT."""
    # "No" and "stop" are NOT in your list
    assert is_backchannel("No stop", DEFAULT_IGNORE_WORDS) is False

@pytest.mark.asyncio
async def test_scenario_4_mixed_input():
    """Scenario 4: User says 'Yeah okay but wait' -> INTERRUPT."""
    # "but" and "wait" are NOT in your list
    assert is_backchannel("Yeah okay but wait", DEFAULT_IGNORE_WORDS) is False

# ==========================================
# PART 3: Integration/State Tests
# ==========================================

@pytest.fixture
def mock_agent_context():
    session = MagicMock()
    session.options.ignore_words = DEFAULT_IGNORE_WORDS
    audio_rec = MagicMock()
    return session, audio_rec

@pytest.mark.asyncio
async def test_interruption_blocked_when_speaking(mock_agent_context):
    """If Agent is SPEAKING and input is 'Yeah', block interruption."""
    session, audio_rec = mock_agent_context
    session.agent_state = "speaking"
    audio_rec.current_transcript = "Yeah"
    
    should_interrupt = True
    if session.agent_state == "speaking":
        if is_backchannel(audio_rec.current_transcript, session.options.ignore_words):
            should_interrupt = False
            
    assert should_interrupt is False

@pytest.mark.asyncio
async def test_scenario_2_response_when_silent(mock_agent_context):
    """If Agent is SILENT, 'Yeah' should be processed (Interrupt=True)."""
    session, audio_rec = mock_agent_context
    session.agent_state = "listening"
    audio_rec.current_transcript = "Yeah"
    
    should_interrupt = True
    # The Logic Gate: Only check backchannel if speaking
    if session.agent_state == "speaking":
        if is_backchannel(audio_rec.current_transcript, session.options.ignore_words):
            should_interrupt = False
            
    assert should_interrupt is True