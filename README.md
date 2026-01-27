<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>SalesCode AI Agents Assignment</title>
<style>
    body {
        font-family: Arial, sans-serif;
        max-width: 900px;
        margin: auto;
        line-height: 1.6;
        color: #222;
    }
    h1, h2, h3 {
        color: #0b3d91;
    }
    code, pre {
        background: #f4f4f4;
        padding: 8px;
        display: block;
        border-radius: 4px;
        overflow-x: auto;
    }
    table {
        border-collapse: collapse;
        width: 100%;
        margin-top: 10px;
    }
    th, td {
        border: 1px solid #ccc;
        padding: 8px;
        text-align: left;
    }
    th {
        background: #f0f0f0;
    }
</style>
</head>
<body>

<h1>SalesCode AI Agents Assignment</h1>

<h2>Overview</h2>
<p>
This repository contains the LiveKit Agents assignment implementation.  
The objective of this task was to improve real-time voice agent interruption handling where short acknowledgement words such as 
<b>"yeah"</b> were causing unintended speech interruptions due to VAD triggering faster than STT.
</p>

<p>
The provided tests validate transcription filtering logic.  
The implemented solution introduces an <b>agent-side interruption handling layer</b> without modifying the low-level VAD kernel 
and without adding perceptible latency.
</p>

<hr>

<h2>Requirements</h2>
<ul>
<li>Python 3.9+</li>
<li>LiveKit Cloud account (or local LiveKit server)</li>
<li>Model provider API key (OpenAI, Groq, Gemini, etc.)</li>
</ul>

<hr>

<h2>Installation</h2>

<p>Clone your fork:</p>
<pre>git clone &lt;your-fork-url&gt;
cd salescode-ai-agents-assignment</pre>

<p>Create a virtual environment:</p>
<pre>python -m venv venv
venv\Scripts\activate</pre>

<p>Install dependencies:</p>
<pre>pip install -r requirements.txt</pre>

<hr>

<h2>Environment Variables</h2>

<p>Create a <code>.env</code> file in the project root:</p>

<pre>
LIVEKIT_URL="wss://your-project.livekit.cloud"
LIVEKIT_API_KEY="your_livekit_api_key"
LIVEKIT_API_SECRET="your_livekit_api_secret"

OPENAI_API_KEY="your_model_api_key"
</pre>

<p>
The <code>.env</code> file is included in <code>.gitignore</code> to prevent credential leaks.
</p>

<hr>

<h2>Running Tests</h2>

<pre>pytest tests</pre>

<p>All provided tests should pass.</p>

<hr>

<h2>Running the Example Agent</h2>

<pre>python examples/minimal_worker.py</pre>

<p>
Open the LiveKit web room or Agents Playground and join the configured room to interact with the agent.
</p>

<hr>

<h2>Interruption Handling Logic</h2>

<h3>Problem</h3>

<p>
Voice Activity Detection (VAD) triggers immediately when user speech begins, while Speech-to-Text (STT) finalizes slightly later.  
Short acknowledgement utterances like:
</p>

<ul>
<li>"yeah"</li>
<li>"ok"</li>
<li>"uh-huh"</li>
</ul>

<p>
were causing <b>false interruptions</b> by cutting off the agent mid-speech.
</p>

<p>
The assignment required fixing this:
</p>

<ul>
<li>Without modifying the VAD kernel</li>
<li>Without adding noticeable latency</li>
<li>By implementing logic inside the agent event loop</li>
</ul>

<hr>

<h3>Solution</h3>

<p>
A transcription validation layer was added in:
</p>

<pre>examples/minimal_worker.py</pre>

<p>
Instead of reacting directly to VAD triggers, the agent now waits for <b>final STT transcripts</b> before deciding whether to interrupt or ignore input.
</p>

<hr>

<h3>Implementation Details</h3>

<h4>1. Agent Speaking State Tracking</h4>
<p>
The agent tracks whether it is currently speaking using AgentSession state events.
This determines when interruption filtering rules apply.
</p>

<h4>2. Final Transcript Inspection</h4>
<p>
Only final STT transcripts are processed. Partial transcripts are ignored to prevent premature interruption.
</p>

<h4>3. Filler Word Filtering</h4>

<pre>{"yeah", "ok", "okay", "uh", "hmm", "mm", "mmhmm"}</pre>

<p>
If:
</p>
<ul>
<li>The agent is speaking</li>
<li>The transcript contains only filler words</li>
</ul>
<p>
Then the transcript is discarded and no interruption occurs.
</p>

<h4>4. Intentional Interruption Detection</h4>

<pre>{"stop", "wait", "hold", "pause", "no"}</pre>

<p>
If:
</p>
<ul>
<li>The agent is speaking</li>
<li>The transcript contains an interruption keyword</li>
</ul>

<p>
Then:
</p>

<pre>session.interrupt()</pre>

<p>
is called to immediately stop agent speech.
</p>

<h4>5. Normal Turn-Taking</h4>
<p>
If the agent is not speaking, all user transcripts — including short acknowledgements — are processed normally.
</p>

<hr>

<h3>Resulting Behavior</h3>

<table>
<tr>
<th>Scenario</th>
<th>Behavior</th>
</tr>
<tr>
<td>Agent speaking + user says "yeah"</td>
<td>Ignored</td>
</tr>
<tr>
<td>Agent silent + user says "yeah"</td>
<td>Processed normally</td>
</tr>
<tr>
<td>Agent speaking + user says "stop"</td>
<td>Agent speech stops immediately</td>
</tr>
<tr>
<td>Agent speaking + user says "yeah wait"</td>
<td>Agent interrupted</td>
</tr>
</table>

<hr>

<h3>Performance</h3>

<ul>
<li>No VAD kernel modifications</li>
<li>No perceptible latency added</li>
<li>Fully real-time operation</li>
<li>Stable conversational turn-taking</li>
</ul>

<hr>

<h2>Submission Notes</h2>

<ul>
<li>Feature branch: <code>feature/interrupt-handler-&lt;yourname&gt;</code></li>
<li>Logic committed with interruption handler</li>
<li><code>.env</code> added to <code>.gitignore</code></li>
<li>Logs or video demonstration can be attached showing:</li>
<ul>
<li>Agent ignores "yeah" while speaking</li>
<li>Agent responds to "yeah" when silent</li>
<li>Agent stops on "stop"</li>
</ul>
</ul>

<hr>

<h2>Notes</h2>

<p>
Any supported LiveKit LLM plugin can be used.  
Place the corresponding API key in the <code>.env</code> file.
</p>

<hr>

<h2>Author</h2>

<p>
Pratham Rathod<br>
SalesCode AI Agents Assignment Submission
</p>

</body>
</html>
