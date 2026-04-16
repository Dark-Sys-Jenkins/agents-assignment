

<h1>LiveKit Intelligent Interruption Handling 
Challenge </h1>

<h2>🚀 Overview</h2>
<p>
This project implements a <b>context-aware interruption handling system</b> for a real-time voice AI agent using the LiveKit framework.
</p>

<p>
Traditional voice agents incorrectly treat small acknowledgements like <i>"yeah", "ok"</i> as interruptions.  
This system intelligently distinguishes between <b>passive acknowledgements</b> and <b>active interruptions</b>.
</p>

<hr>

<h2>🧠 Problem Statement</h2>
<ul>
  <li>Users often say filler words while listening</li>
  <li>Default VAD interprets them as interruptions</li>
  <li>Agent stops speaking unnecessarily ❌</li>
</ul>

<p><b>Goal:</b> Build a system that understands user intent and reacts correctly.</p>

<hr>

<h2>⚙️ System Architecture</h2>
<pre>
User Voice → VAD → STT → classify_input() → Decision → Agent Action
</pre>

<hr>

<h2>📂 Project Structure</h2>
<pre>
voice_agent/
│
├── main.py
├── interrupt_handler.py
├── state_manager.py
├── transcript_handler.py
├── .env
</pre>

<hr>

<h2>📄 File Explanation</h2>

<h3>🔹 main.py</h3>
<ul>
  <li>Initializes the agent session</li>
  <li>Connects VAD, STT, LLM, TTS</li>
  <li>Registers event handlers</li>
</ul>

<p><b>Role:</b> Main controller of the system</p>

---

<h3>🔹 interrupt_handler.py</h3>
<p>Core decision-making logic:</p>

<pre>
classify_input(text, is_agent_speaking)
</pre>

<p>Returns:</p>
<ul>
  <li><b>IGNORE</b> → continue speaking</li>
  <li><b>INTERRUPT</b> → stop agent</li>
  <li><b>RESPOND</b> → normal reply</li>
</ul>

---

<h3>🔹 state_manager.py</h3>
<ul>
  <li>Tracks agent state</li>
  <li>Maintains: <code>is_agent_speaking</code></li>
</ul>

---

<h3>🔹 transcript_handler.py</h3>
<ul>
  <li>Processes user speech</li>
  <li>Calls decision logic</li>
  <li>Executes actions</li>
</ul>

<hr>

<h2>🧪 Scenarios & Solutions</h2>

<h3>✅ Scenario 1: Long Explanation</h3>
<p><b>Input:</b> "yeah okay hmm"</p>
<p><b>Result:</b> Agent continues speaking (IGNORE)</p>

---

<h3>✅ Scenario 2: Passive Affirmation</h3>
<p><b>Input:</b> "yeah" (when silent)</p>
<p><b>Result:</b> Agent responds normally (RESPOND)</p>

---

<h3>✅ Scenario 3: Correction</h3>
<p><b>Input:</b> "no stop"</p>
<p><b>Result:</b> Agent stops immediately (INTERRUPT)</p>

---

<h3>✅ Scenario 4: Mixed Input</h3>
<p><b>Input:</b> "yeah okay but wait"</p>
<p><b>Result:</b> Agent stops (INTERRUPT)</p>

<hr>

<h2>⚡ Key Features</h2>
<ul>
  <li>Context-aware interruption handling</li>
  <li>Real-time decision making</li>
  <li>Handles mixed and noisy speech inputs</li>
  <li>Modular architecture</li>
</ul>

<hr>

<h2>🔑 Technologies Used</h2>
<ul>
  <li>LiveKit Agents</li>
  <li>Groq LLM (LLaMA 3.1)</li>
  <li>Deepgram (STT)</li>
  <li>ElevenLabs / Cartesia (TTS)</li>
  <li>Python (Async Programming)</li>
</ul>

<hr>

<h2>▶️ How to Run</h2>
<pre>
pip install -e .
pip install -r requirements.txt
python main.py console
</pre>

<hr>

<h2>🎤 Test Commands</h2>
<pre>
yeah okay hmm   → IGNORE
no stop         → INTERRUPT
yeah            → RESPOND
hello           → RESPOND
</pre>

<hr>

<h2>🎥 Demo Video</h2>
<p>
<a href="https://drive.google.com/file/d/107Zc57PlQg41VAcZ3j7ns8wzJC09NlEW/view?usp=sharing">👉 Add your demo video link here</a>
</p>

<hr>

<h2>🏁 Conclusion</h2>
<p>
This system successfully implements a <b>state-aware intelligent interruption handler</b> that improves conversational flow and mimics human-like interaction.
</p>

<hr>

<h2>👨‍💻 Author</h2>
<p>Aditya Kumar</p>

</body>
</html>
