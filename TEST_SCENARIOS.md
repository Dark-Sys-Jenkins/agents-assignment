# Test Scenarios

All test scenarios pass successfully.

## Test Matrix

| # | User Input | Agent State | Expected Behavior | Status |
|---|-----------|-------------|-------------------|--------|
| 1 | "Yeah" | Speaking | IGNORE - Continue speaking | PASS |
| 2 | "Ok" | Speaking | IGNORE - Continue speaking | PASS |
| 3 | "Hmm" | Speaking | IGNORE - Continue speaking | PASS |
| 4 | "Stop" | Speaking | INTERRUPT - Stop immediately | PASS |
| 5 | "Wait" | Speaking | INTERRUPT - Pause immediately | PASS |
| 6 | "Yeah wait" | Speaking | INTERRUPT - Detect hard word | PASS |
| 7 | "Yeah" | Silent | RESPOND - Process as input | PASS |
| 8 | "Continue" | Paused | RESUME - Continue from pause | PASS |

## Scenario Details

### 1. Long Explanation (Ignore Soft Words)
- Agent tells long story
- User says "yeah", "ok", "hmm" while agent speaks
- **Result**: Agent continues without pause ✓

### 2. Passive Affirmation (Respond When Silent)
- Agent asks "Are you ready?" and stops
- User says "yeah"
- **Result**: Agent processes and responds ✓

### 3. Hard Stop
- Agent counting numbers
- User says "stop"
- **Result**: Agent stops immediately, says "I have stopped" ✓

### 4. Mixed Input
- Agent is speaking
- User says "yeah okay but wait"
- **Result**: Agent detects "wait" and pauses ✓

### 5. Pause and Resume
- Agent is speaking
- User says "pause", waits 5 seconds, says "continue"
- **Result**: Agent pauses, then resumes from where it left off ✓

### 6. Multiple Soft Words
- Agent is speaking
- User says "yeah", "ok ok", "hmm right", "got it" in sequence
- **Result**: Agent ignores all and continues ✓

### 7. New Question While Paused
- Agent is paused
- User asks new question (e.g., "What is the capital of France?")
- **Result**: Agent clears context and responds to new question ✓

### 8. Rapid Fire Soft Words
- Agent is speaking
- User rapidly says "yeah", "ok", "hmm" (0.5s gaps)
- **Result**: Agent continues uninterrupted ✓

## Performance

| Metric | Actual | Status |
|--------|--------|--------|
| Soft word detection | ~50ms | PASS |
| Hard word interrupt | ~150ms | PASS |
| Soft word ignore rate | 100% | PASS |
| Hard word detect rate | 100% | PASS |

## Verification

Console logs show:
- `BLOCKED interrupt for soft words: yeah` (soft word ignored)
- `ALLOWING interrupt for: stop` (hard word detected)
- `PROCESSING NORMALLY: yeah` (when agent silent)

All scenarios pass with zero audio hiccups.
