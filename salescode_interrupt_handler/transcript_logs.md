venv) PS C:\Users\manav\Videos\liv\agents-assignment\examples\voice_agents> python trial4.py console  
 Agents Starting console mode 🚀

    16:50:53.058 DEBUG… asyncio            Using proactor: IocpProactor
    16:50:53.066 INFO … livekit.agents     starting worker {"version": "1.3.12", "rtc-version": "1.0.23"}
    16:50:53.067 INFO … livekit.agents     starting inference executor
    16:50:53.102 INFO … livekit.agents     initializing process {"pid": 25252, "inference": true}
    16:51:21.863 INFO … livekit.agents     process initialized {"pid": 25252, "inference": true, "elapsed_time": 28.76}
    16:51:21.867 INFO … livekit.agents     HTTP server listening on :53628
    16:51:21.880 INFO … livekit.agents     initializing job runner {"tid": 24348}
    16:51:22.022 DEBUG… asyncio            Using proactor: IocpProactor
    16:51:22.024 INFO … livekit.agents     job runner initialized {"tid": 24348, "elapsed_time": 0.14}
    16:51:22.079 INFO … salescod…ntroller2 InterruptionController initialized with 34 ignore words and 18 interrupt words {"room": "console"}
    16:51:22.081 INFO … intelligent-agent  ✓ InterruptionController initialized {"room": "console"}
    16:51:22.083 INFO … intelligent-agent  ✓ Stats: {'current_state': 'listening', 'ignore_words_count': 34, 'interrupt_words_count': 18, 'grace_period_seconds': 0.5, 'time_since_speaking': None}
                                           {"room": "console"}
    16:51:22.585 INFO … intelligent-agent  ✓ AgentSession configured with intelligent interrupt handling {"room": "console"}
    16:51:22.591 DEBUG… livekit.agents     http_session(): creating a new httpclient ctx {"room": "console"}
    16:51:23.095 DEBUG… salescod…ntroller2 Agent state: listening → listening {"room": "console"}
    16:51:23.096 DEBUG… intelligent-agent  [STATE] initializing → listening {"room": "console"}
    16:51:23.098 DEBUG… livekit.agents     using audio io: `Console` -> `AgentSession` -> `TranscriptSynchronizer` -> `Console` {"room": "console"}
    16:51:23.099 DEBUG… livekit.agents     using transcript io: `AgentSession` -> `TranscriptSynchronizer` {"room": "console"}
    16:51:23.100 INFO … intelligent-agent  ✓ Session started successfully {"room": "console"}
    16:51:23.103 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}
    16:51:23.104 DEBUG… intelligent-agent  [STATE] listening → thinking {"room": "console"}
    16:51:23.370 INFO … livekit.agents     LLM metrics
                                         {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.73, "prompt_tokens": 89, "prompt_cached_tokens": 0, "completion_tokens": 14,

"tokens_per_second": 18.24, "room": "console"}
16:51:24.157 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "<redacted>", "dg-request-id": "<redacted>", "Date": "Sat, 31 Jan 2026 11:21:25  
GMT"}, "room": "console"}
16:51:24.479 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.05, "room": "console"}
16:51:24.899 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:51:24.902 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:51:25.979 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7378929999999855, "audio_duration": 3.0, "room": "console"}
16:51:27.965 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858487.9650185 {"room": "console"}
16:51:27.968 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:51:27.970 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:51:29.592 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.1, "room": "console"}
16:51:31.589 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Tell me in' → NO_DECISION {"room": "console"}
16:51:31.591 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Tell me in' (normal input) {"room": "console"}
16:51:31.732 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.2, "room": "console"}
16:51:31.735 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Tell me in' → NO_DECISION {"room": "console"}
16:51:31.736 INFO … intelligent-agent [PROCESSING] 'Tell me in' (normal input, agent silent) {"room": "console"}  
 16:51:31.739 DEBUG… livekit.agents received user transcript {"user_transcript": "Tell me in", "language": "en", "transcript_delay": 0.015108823776245117, "room": "console"}  
 16:51:31.972 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.16, "prompt_tokens": 115, "prompt_cached_tokens": 0, "completion_tokens": 15,  
"tokens_per_second": 65.7, "room": "console"}
16:51:32.705 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'about detail photosynthesis.' → NO_DECISION {"room": "console"}
16:51:32.708 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'about detail photosynthesis.' (normal input) {"room": "console"}
16:51:33.390 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.6, "room": "console"}
16:51:33.393 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'about photosynthesis.' → NO_DECISION {"room": "console"}
16:51:33.395 INFO … intelligent-agent [PROCESSING] 'about photosynthesis.' (normal input, agent silent) {"room": "console"}  
 16:51:33.397 DEBUG… livekit.agents received user transcript {"user_transcript": "about photosynthesis.", "language": "en", "transcript_delay": 0.3739452362060547, "room": "console"}  
 16:51:33.710 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.2, "prompt_tokens": 119, "prompt_cached_tokens": 0, "completion_tokens": 43,  
"tokens_per_second": 139.13, "room": "console"}  
 16:51:33.729 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.16198834776878357, "duration": 0.094, "input": "<|im_start|>assistant\nhi i'm kelly what's on your mind today<|im_end|>\n<|im_start|>user\ntell
me in about photosynthesis", "room": "console"}  
 16:51:33.733 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.33252787590026855, "room": "console"}  
 16:51:33.736 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.71, "transcription_delay": 0.38, "room": "console"}
16:51:33.740 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:51:33.743 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:51:34.642 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "b428cd78-9f7e-4edb-b6c7-63f50d132e73", "Date": "Sat, 31 Jan 2026 11:21:36  
GMT"}, "room": "console"}
16:51:35.370 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:51:35.374 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:51:38.405 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0, "room": "console"}
16:51:39.658 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Yeah.' → IGNORE {"room": "console"}
16:51:39.660 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Yeah.' (backchannel ignored) {"room": "console"}
16:51:41.191 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7204591000000278, "audio_duration": 13.52, "room": "console"}
16:51:43.007 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.25, "room": "console"}
16:51:43.011 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Uh-huh.' → IGNORE {"room": "console"}
16:51:43.013 INFO … intelligent-agent [CLEARED] 'Uh-huh.' (backchannel ignored) {"room": "console"}  
 16:51:43.015 DEBUG… livekit.agents received user transcript {"user_transcript": "Uh-huh.", "language": "en", "transcript_delay": 3.7927122116088867, "room": "console"}  
 16:51:43.116 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.36906903982162476, "duration": 0.096, "input": "<|im_start|>assistant\nhi i'm kelly what's on your mind today<|im_end|>\n<|im_start|>user\ntell
me in about photosynthesis uh-huh", "room": "console"}
16:51:46.216 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.15, "room": "console"}
16:51:48.955 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858508.955297 {"room": "console"}
16:51:48.959 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:51:48.961 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:51:51.206 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0, "room": "console"}
16:51:54.314 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.1, "room": "console"}
16:51:54.358 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Tell me more' → NO_DECISION {"room": "console"}
16:51:54.360 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Tell me more' (normal input) {"room": "console"}
16:51:54.707 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.4, "room": "console"}
16:51:54.709 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Tell me more about' → NO_DECISION {"room": "console"}  
 16:51:54.711 INFO … intelligent-agent [PROCESSING] 'Tell me more about' (normal input, agent silent) {"room": "console"}  
 16:51:54.713 DEBUG… livekit.agents received user transcript {"user_transcript": "Tell me more about", "language": "en", "transcript_delay": 0.3927168846130371, "room": "console"}  
 16:51:55.034 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.2, "prompt_tokens": 179, "prompt_cached_tokens": 0, "completion_tokens": 42,  
"tokens_per_second": 131.99, "room": "console"}
16:51:55.713 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'photosynthesis.' → NO_DECISION {"room": "console"}
16:51:55.716 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'photosynthesis.' (normal input) {"room": "console"}  
 16:51:56.099 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.4, "room": "console"}
16:51:56.102 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'photosynthesis.' → NO_DECISION {"room": "console"}  
 16:51:56.105 INFO … intelligent-agent [PROCESSING] 'photosynthesis.' (normal input, agent silent) {"room": "console"}  
 16:51:56.106 DEBUG… livekit.agents received user transcript {"user_transcript": "photosynthesis.", "language": "en", "transcript_delay": 0.07796120643615723, "room": "console"}  
 16:51:56.528 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.3, "prompt_tokens": 182, "prompt_cached_tokens": 0, "completion_tokens": 61,  
"tokens_per_second": 145.9, "room": "console"}
16:51:57.017 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.9, "room": "console"}
16:51:57.021 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'In detail.' → NO_DECISION {"room": "console"}  
 16:51:57.023 INFO … intelligent-agent [PROCESSING] 'In detail.' (normal input, agent silent) {"room": "console"}  
 16:51:57.025 DEBUG… livekit.agents received user transcript {"user_transcript": "In detail.", "language": "en", "transcript_delay": 0.40293121337890625, "room": "console"}  
 16:51:57.286 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.677756130695343, "duration": 0.159, "input": "<|im_start|>assistant\nhi i'm kelly what's on your mind today<|im_end|>\n<|im_start|>user\ntell  
me in about photosynthesis<|im_end|>\n<|im_start|>assistant\nphotosynthesis is how plants make food from sunlight water and carbon dioxide they release oxygen as a byproduct which is pretty handy for the rest
of us want to know more about the process<|im_end|>\n<|im_start|>user\nuh-huh tell me more about photosynthesis in detail", "room": "console"}
16:51:57.290 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.26246070861816406, "room": "console"}  
 16:51:57.292 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.67, "transcription_delay": 0.4, "room": "console"}  
 16:51:57.295 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:51:57.298 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:51:57.840 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.33, "prompt_tokens": 185, "prompt_cached_tokens": 0, "completion_tokens": 124,  
"tokens_per_second": 152.69, "room": "console"}
16:51:58.147 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "38b88ccb-a5bb-4b1e-acb8-89648714641e", "Date": "Sat, 31 Jan 2026 11:21:59  
GMT"}, "room": "console"}  
 16:51:58.738 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:51:58.741 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:52:02.010 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0, "room": "console"}
16:52:04.994 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Yeah.' → IGNORE {"room": "console"}
16:52:04.997 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Yeah.' (backchannel ignored) {"room": "console"}
16:52:09.900 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.85, "room": "console"}
16:52:09.903 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Yep.' → IGNORE {"room": "console"}
16:52:09.905 INFO … intelligent-agent [CLEARED] 'Yep.' (backchannel ignored) {"room": "console"}  
 16:52:09.908 DEBUG… livekit.agents received user transcript {"user_transcript": "Yep.", "language": "en", "transcript_delay": 5.280853509902954, "room": "console"}  
 16:52:10.117 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.44825825095176697, "duration": 0.203, "input": "<|im_start|>assistant\nhi i'm kelly what's on your mind today<|im_end|>\n<|im_start|>user\ntell
me in about photosynthesis<|im_end|>\n<|im_start|>assistant\nphotosynthesis is how plants make food from sunlight water and carbon dioxide they release oxygen as a byproduct which is pretty handy for the rest
of us want to know more about the process<|im_end|>\n<|im_start|>user\nuh-huh tell me more about photosynthesis in detail yep", "room": "console"}
16:52:13.197 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Yes.' → IGNORE {"room": "console"}
16:52:13.200 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Yes.' (backchannel ignored) {"room": "console"}
16:52:17.863 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.5873343999999747, "audio_duration": 42.4, "room": "console"}
16:52:18.492 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:52:18.534 INFO … salescod…ntroller2 [DECISION] Unknown words while speaking: ['hello'] → INTERRUPT {"room": "console"}
16:52:18.536 DEBUG… intelligent-agent [INTERRUPTED-INTERIM] 'Hello,' (command detected) {"room": "console"}  
 16:52:18.541 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858538.54144 {"room": "console"}
16:52:18.543 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:52:18.545 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:52:23.889 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:52:26.312 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.4, "room": "console"}
16:52:28.325 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Thank' → NO_DECISION {"room": "console"}
16:52:28.328 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Thank' (normal input) {"room": "console"}
16:52:28.899 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.6, "room": "console"}
16:52:28.902 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Continue.' → NO_DECISION {"room": "console"}
16:52:28.903 INFO … intelligent-agent [PROCESSING] 'Continue.' (normal input, agent silent) {"room": "console"}  
 16:52:28.905 DEBUG… livekit.agents received user transcript {"user_transcript": "Continue.", "language": "en", "transcript_delay": 10.48436713218689, "room": "console"}  
 16:52:29.180 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.0709909200668335, "duration": 0.266, "input": "<|im_start|>assistant\nhi i'm kelly what's on your mind today<|im_end|>\n<|im_start|>user\ntell
me in about photosynthesis<|im_end|>\n<|im_start|>assistant\nphotosynthesis is how plants make food from sunlight water and carbon dioxide they release oxygen as a byproduct which is pretty handy for the rest
of us want to know more about the process<|im_end|>\n<|im_start|>user\nuh-huh tell me more about photosynthesis in detail<|im_end|>\n<|im_start|>assistant\nphotosynthesis happens in special parts of plant  
cells called chloroplasts it's a two-part process first light energy from the sun is absorbed by a green pigment called chlorophyll this energy is used to convert water and carbon dioxide into a type of sugar
that the plant uses for food the<|im_end|>\n<|im_start|>user\ncontinue", "room": "console"}
16:52:29.184 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.27609992027282715, "room": "console"}  
 16:52:29.185 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 10.76, "transcription_delay": 10.49, "room": "console"}  
 16:52:29.187 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:52:29.190 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:52:29.434 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.29, "prompt_tokens": 260, "prompt_cached_tokens": 0, "completion_tokens": 98,  
"tokens_per_second": 186.71, "room": "console"}
16:52:29.811 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:52:29.814 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:52:34.056 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.2, "room": "console"}
16:52:36.607 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Yes.' → IGNORE {"room": "console"}
16:52:36.609 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Yes.' (backchannel ignored) {"room": "console"}  
 16:52:38.052 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.45, "room": "console"}
16:52:38.055 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['wait'] → INTERRUPT {"room": "console"}
16:52:38.058 INFO … intelligent-agent [INTERRUPTED] 'Wait.' (command/real input detected) {"room": "console"}  
 16:52:38.060 DEBUG… livekit.agents received user transcript {"user_transcript": "Wait.", "language": "en", "transcript_delay": 1.0368220806121826, "room": "console"}  
 16:52:38.082 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858558.082502 {"room": "console"}
16:52:38.086 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:52:38.090 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:52:38.375 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.036898862570524216, "duration": 0.302, "input": "<|im_start|>user\ntell me in about
photosynthesis<|im_end|>\n<|im_start|>assistant\nphotosynthesis is how plants make food from sunlight water and carbon dioxide they release oxygen as a byproduct which is pretty handy for the rest of us want
to know more about the process<|im_end|>\n<|im_start|>user\nuh-huh tell me more about photosynthesis in detail<|im_end|>\n<|im_start|>assistant\nphotosynthesis happens in special parts of plant cells called  
chloroplasts it's a two-part process first light energy from the sun is absorbed by a green pigment called chlorophyll this energy is used to convert water and carbon dioxide into a type of sugar that the  
plant uses for food the<|im_end|>\n<|im_start|>user\ncontinue wait", "room": "console"}
16:52:38.381 WARNI… livekit.agents preemptive generation enabled but chat context or tools have changed after `on_user_turn_completed` {"room": "console"}  
 16:52:38.384 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 1.36, "transcription_delay": 1.04, "room": "console"}  
 16:52:38.394 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}
16:52:38.395 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:52:38.399 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.28, "prompt_tokens": 0, "prompt_cached_tokens": 0, "completion_tokens": 0,  
"tokens_per_second": 0.0, "room": "console"}  
 16:52:38.773 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.33, "prompt_tokens": 298, "prompt_cached_tokens": 0, "completion_tokens": 16,  
"tokens_per_second": 41.61, "room": "console"}
16:52:39.799 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "a31ff5e3-a58f-4e55-9c45-aa68e4ec1a19", "Date": "Sat, 31 Jan 2026 11:22:41  
GMT"}, "room": "console"}  
 16:52:40.538 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:52:40.541 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:52:41.560 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7354087999999592, "audio_duration": 2.96, "room": "console"}
16:52:43.398 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:52:43.462 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858563.4627686 {"room": "console"}
16:52:43.464 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:52:43.467 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:52:46.204 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.8, "room": "console"}
16:52:47.198 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['no', 'no'] → INTERRUPT {"room": "console"}
16:52:47.200 DEBUG… intelligent-agent [INTERRUPTED-INTERIM] 'No. No. Continue.' (command detected) {"room": "console"}
16:52:52.495 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:52:57.087 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.6, "room": "console"}
16:52:57.389 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Yeah. And' → NO_DECISION {"room": "console"}
16:52:57.391 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Yeah. And' (normal input) {"room": "console"}
16:52:57.914 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.8, "room": "console"}
16:52:57.917 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Carry on.' → NO_DECISION {"room": "console"}  
 16:52:57.919 INFO … intelligent-agent [PROCESSING] 'Carry on.' (normal input, agent silent) {"room": "console"}  
 16:52:57.921 DEBUG… livekit.agents received user transcript {"user_transcript": "Carry on.", "language": "en", "transcript_delay": 0.49959683418273926, "room": "console"}  
 16:52:58.157 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.4642004072666168, "duration": 0.219, "input": "<|im_start|>assistant\nphotosynthesis happens in special parts of plant cells called
chloroplasts it's a two-part process first light energy from the sun is absorbed by a green pigment called chlorophyll this energy is used to convert water and carbon dioxide into a type of sugar that the  
plant uses for food the<|im_end|>\n<|im_start|>user\ncontinue<|im_end|>\n<|im_start|>assistant\nthe second part of the process is called the calvin cycle it's where the plant uses the energy from light to  
convert carbon dioxide<|im_end|>\n<|im_start|>user\nwait<|im_end|>\n<|im_start|>assistant\nwhat's up do you have a question about what i was saying<|im_end|>\n<|im_start|>user\ncarry on", "room": "console"}  
 16:52:58.161 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.23743891716003418, "room": "console"}  
 16:52:58.163 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.74, "transcription_delay": 0.5, "room": "console"}  
 16:52:58.165 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:52:58.167 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:52:58.400 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.29, "prompt_tokens": 327, "prompt_cached_tokens": 0, "completion_tokens": 75,  
"tokens_per_second": 157.86, "room": "console"}  
 16:52:59.014 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:52:59.017 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:53:02.895 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0, "room": "console"}
16:53:05.993 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.1, "room": "console"}
16:53:06.390 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.4, "room": "console"}
16:53:07.395 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['wait'] → INTERRUPT {"room": "console"}
16:53:07.397 DEBUG… intelligent-agent [INTERRUPTED-INTERIM] 'Wait a minute.' (command detected) {"room": "console"}
16:53:07.407 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858587.4070868 {"room": "console"}  
 16:53:07.409 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:53:07.411 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:53:12.612 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.15, "room": "console"}
16:53:13.486 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Continue.' → NO_DECISION {"room": "console"}
16:53:13.489 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Continue.' (normal input) {"room": "console"}
16:53:14.284 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.7, "room": "console"}
16:53:14.287 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Continue. Continue.' → NO_DECISION {"room": "console"}
16:53:14.295 INFO … intelligent-agent [PROCESSING] 'Continue. Continue.' (normal input, agent silent) {"room": "console"}  
 16:53:14.299 DEBUG… livekit.agents received user transcript {"user_transcript": "Continue. Continue.", "language": "en", "transcript_delay": 0.4756488800048828, "room": "console"}
16:53:14.601 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.6357380151748657, "duration": 0.177, "input": "<|im_start|>assistant\nthe second part of the process is called the calvin cycle it's where the
plant uses the energy from light to convert carbon dioxide<|im_end|>\n<|im_start|>user\nwait<|im_end|>\n<|im_start|>assistant\nwhat's up do you have a question about what i was
saying<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nso the calvin cycle is where the plant uses the energy from light to convert carbon dioxide into glucose which is a type  
of<|im_end|>\n<|im_start|>user\ncontinue continue", "room": "console"}
16:53:14.605 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.30129218101501465, "room": "console"}  
 16:53:14.608 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.78, "transcription_delay": 0.48, "room": "console"}  
 16:53:14.611 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:53:14.613 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}
16:53:14.672 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.17, "prompt_tokens": 366, "prompt_cached_tokens": 0, "completion_tokens": 67,  
"tokens_per_second": 182.2, "room": "console"}
16:53:15.508 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "0a46cc8b-15d8-421a-81a0-fb2b2516ec25", "Date": "Sat, 31 Jan 2026 11:23:17  
GMT"}, "room": "console"}
16:53:16.237 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:53:16.241 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:53:19.283 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0, "room": "console"}
16:53:22.685 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.4, "room": "console"}
16:53:24.785 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.1, "room": "console"}
16:53:24.788 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Uh-huh.' → IGNORE {"room": "console"}  
 16:53:24.790 INFO … intelligent-agent [CLEARED] 'Uh-huh.' (backchannel ignored) {"room": "console"}  
 16:53:24.792 DEBUG… livekit.agents received user transcript {"user_transcript": "Uh-huh.", "language": "en", "room": "console"}
16:53:24.946 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.6719324588775635, "duration": 0.144, "input": "<|im_start|>user\nwait<|im_end|>\n<|im_start|>assistant\nwhat's up do you have a question about
what i was saying<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nso the calvin cycle is where the plant uses the energy from light to convert carbon dioxide into glucose which is a  
type of<|im_end|>\n<|im_start|>user\ncontinue continue uh-huh", "room": "console"}
16:53:28.095 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.25, "room": "console"}
16:53:28.097 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Uh-huh.' → IGNORE {"room": "console"}
16:53:28.100 INFO … intelligent-agent [CLEARED] 'Uh-huh.' (backchannel ignored) {"room": "console"}  
 16:53:28.102 DEBUG… livekit.agents received user transcript {"user_transcript": "Uh-huh.", "language": "en", "transcript_delay": 3.307488203048706, "room": "console"}  
 16:53:28.241 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.6719324588775635, "duration": 0.134, "input": "<|im_start|>user\nwait<|im_end|>\n<|im_start|>assistant\nwhat's up do you have a question about
what i was saying<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nso the calvin cycle is where the plant uses the energy from light to convert carbon dioxide into glucose which is a  
type of<|im_end|>\n<|im_start|>user\ncontinue continue uh-huh", "room": "console"}
16:53:28.499 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7271518999999671, "audio_duration": 27.0, "room": "console"}
16:53:32.796 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.65, "room": "console"}
16:53:32.798 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Alright.' → IGNORE {"room": "console"}  
 16:53:32.801 INFO … intelligent-agent [CLEARED] 'Alright.' (backchannel ignored) {"room": "console"}
16:53:32.802 DEBUG… livekit.agents received user transcript {"user_transcript": "Alright.", "language": "en", "transcript_delay": 8.007858514785767, "room": "console"}  
 16:53:32.945 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.3030685782432556, "duration": 0.136, "input": "<|im_start|>user\nwait<|im_end|>\n<|im_start|>assistant\nwhat's up do you have a question about
what i was saying<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nso the calvin cycle is where the plant uses the energy from light to convert carbon dioxide into glucose which is a  
type of<|im_end|>\n<|im_start|>user\ncontinue continue alright", "room": "console"}
16:53:37.834 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.05, "room": "console"}
16:53:39.189 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.3, "room": "console"}
16:53:39.191 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['stop'] → INTERRUPT {"room": "console"}
16:53:39.193 INFO … intelligent-agent [INTERRUPTED] 'Stop.' (command/real input detected) {"room": "console"}  
 16:53:39.195 DEBUG… livekit.agents received user transcript {"user_transcript": "Stop.", "language": "en", "transcript_delay": 14.40109896659851, "room": "console"}  
 16:53:39.206 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858619.2064629 {"room": "console"}
16:53:39.208 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:53:39.212 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:53:39.357 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.28808480501174927, "duration": 0.151, "input": "<|im_start|>user\nwait<|im_end|>\n<|im_start|>assistant\nwhat's up do you have a question about
what i was saying<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nso the calvin cycle is where the plant uses the energy from light to convert carbon dioxide into glucose which is a  
type of<|im_end|>\n<|im_start|>user\ncontinue continue stop", "room": "console"}
16:53:39.361 WARNI… livekit.agents preemptive generation enabled but chat context or tools have changed after `on_user_turn_completed` {"room": "console"}  
 16:53:39.364 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.0, "transcription_delay": 0.0, "room": "console"}  
 16:53:39.372 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}
16:53:39.373 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:53:39.801 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.37, "prompt_tokens": 433, "prompt_cached_tokens": 0, "completion_tokens": 20,  
"tokens_per_second": 46.06, "room": "console"}  
 16:53:40.522 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:53:40.524 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:53:42.329 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7715474999999969, "audio_duration": 4.64, "room": "console"}
16:53:44.518 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:53:45.157 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858625.1578953 {"room": "console"}
16:53:45.159 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:53:45.161 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:53:47.310 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.8, "room": "console"}
16:53:48.305 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['no'] → INTERRUPT {"room": "console"}
16:53:48.307 DEBUG… intelligent-agent [INTERRUPTED-INTERIM] 'No. Can' (command detected) {"room": "console"}
16:53:50.015 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Tell me about' → NO_DECISION {"room": "console"}
16:53:50.018 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Tell me about' (normal input) {"room": "console"}
16:53:50.255 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.95, "room": "console"}
16:53:50.259 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Tell me about' → NO_DECISION {"room": "console"}  
 16:53:50.261 INFO … intelligent-agent [PROCESSING] 'Tell me about' (normal input, agent silent) {"room": "console"}  
 16:53:50.263 DEBUG… livekit.agents received user transcript {"user_transcript": "Tell me about", "language": "en", "transcript_delay": 0.03883218765258789, "room": "console"}
16:53:50.568 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.21, "prompt_tokens": 465, "prompt_cached_tokens": 0, "completion_tokens": 25,  
"tokens_per_second": 83.18, "room": "console"}
16:53:51.018 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'a rational' → NO_DECISION {"room": "console"}
16:53:51.021 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'a rational' (normal input) {"room": "console"}
16:53:51.537 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.3, "room": "console"}
16:53:51.542 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'rational numbers.' → NO_DECISION {"room": "console"}
16:53:51.544 INFO … intelligent-agent [PROCESSING] 'rational numbers.' (normal input, agent silent) {"room": "console"}  
 16:53:51.548 DEBUG… livekit.agents received user transcript {"user_transcript": "rational numbers.", "language": "en", "transcript_delay": 0.519258975982666, "room": "console"}  
 16:53:51.925 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.22, "prompt_tokens": 468, "prompt_cached_tokens": 0, "completion_tokens": 50,  
"tokens_per_second": 137.88, "room": "console"}
16:53:52.049 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.3211730718612671, "duration": 0.24, "input": "<|im_start|>assistant\nso the calvin cycle is where the plant uses the energy from light to  
convert carbon dioxide into glucose which is a type of<|im_end|>\n<|im_start|>user\ncontinue continue<|im_end|>\n<|im_start|>assistant\nsugar that the plant uses for energy and growth oxygen is also released
as a byproduct of photosynthesis which is really important for humans and other animals because we need oxygen to breathe the overall equation for photosynthesis is six carbon dioxide molecules plus six water
molecules plus<|im_end|>\n<|im_start|>user\nstop<|im_end|>\n<|im_start|>assistant\nwe were in the middle of talking about photosynthesis what would you like to do next<|im_end|>\n<|im_start|>user\ntell me  
about rational numbers", "room": "console"}
16:53:52.054 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.5012156963348389, "room": "console"}  
 16:53:52.056 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 1.02, "transcription_delay": 0.52, "room": "console"}  
 16:53:52.058 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:53:52.060 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:53:52.624 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "4ff71d8f-4265-4020-b2b4-cf3634aaa2cd", "Date": "Sat, 31 Jan 2026 11:23:54  
GMT"}, "room": "console"}
16:53:53.218 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:53:53.222 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:53:56.415 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.8, "room": "console"}
16:54:00.203 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['sorry'] → INTERRUPT {"room": "console"}
16:54:00.207 DEBUG… intelligent-agent [INTERRUPTED-INTERIM] 'Sorry.' (command detected) {"room": "console"}
16:54:00.215 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858640.215044 {"room": "console"}  
 16:54:00.217 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:54:00.220 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:54:05.505 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:54:07.422 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.9, "room": "console"}
16:54:08.403 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Get' → NO_DECISION {"room": "console"}
16:54:08.405 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'Get' (normal input) {"room": "console"}
16:54:09.209 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.8, "room": "console"}
16:54:09.212 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Carry on.' → NO_DECISION {"room": "console"}  
 16:54:09.214 INFO … intelligent-agent [PROCESSING] 'Carry on.' (normal input, agent silent) {"room": "console"}  
 16:54:09.215 DEBUG… livekit.agents received user transcript {"user_transcript": "Carry on.", "language": "en", "transcript_delay": 0.7944722175598145, "room": "console"}  
 16:54:09.473 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.4296826422214508, "duration": 0.242, "input": "<|im_start|>assistant\nsugar that the plant uses for energy and growth oxygen is also released  
as a byproduct of photosynthesis which is really important for humans and other animals because we need oxygen to breathe the overall equation for photosynthesis is six carbon dioxide molecules plus six water
molecules plus<|im_end|>\n<|im_start|>user\nstop<|im_end|>\n<|im_start|>assistant\nwe were in the middle of talking about photosynthesis what would you like to do next<|im_end|>\n<|im_start|>user\ntell me  
about rational numbers<|im_end|>\n<|im_start|>assistant\nrational numbers are numbers that can be expressed as the ratio of two integers like a fraction they<|im_end|>\n<|im_start|>user\ncarry on", "room":  
"console"}
16:54:09.478 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.26005077362060547, "room": "console"}  
 16:54:09.480 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 1.06, "transcription_delay": 0.8, "room": "console"}  
 16:54:09.484 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:54:09.486 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:54:09.623 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.19, "prompt_tokens": 503, "prompt_cached_tokens": 0, "completion_tokens": 84,  
"tokens_per_second": 207.87, "room": "console"}
16:54:10.438 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "50f6c0ed-b2e3-44af-8443-95ce4fefdeef", "Date": "Sat, 31 Jan 2026 11:24:12  
GMT"}, "room": "console"}
16:54:11.178 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:54:11.181 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}  
 16:54:12.121 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.9, "room": "console"}
16:54:14.945 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.9, "room": "console"}
16:54:16.666 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.7, "room": "console"}
16:54:19.416 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.7, "room": "console"}
16:54:20.406 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Makes sense.' → IGNORE {"room": "console"}
16:54:20.408 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Makes sense.' (backchannel ignored) {"room": "console"}
16:54:20.430 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858660.430425 {"room": "console"}
16:54:20.433 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:54:20.435 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:54:25.681 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:54:28.181 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.5, "room": "console"}
16:54:31.980 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.8, "room": "console"}
16:54:31.984 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Yeah.' → NO_DECISION {"room": "console"}
16:54:31.985 INFO … intelligent-agent [PROCESSING] 'Yeah.' (normal input, agent silent) {"room": "console"}  
 16:54:31.987 DEBUG… livekit.agents received user transcript {"user_transcript": "Yeah.", "language": "en", "transcript_delay": 11.866272211074829, "room": "console"}  
 16:54:32.199 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.06594587117433548, "duration": 0.202, "input": "<|im_start|>assistant\nwe were in the middle of talking about photosynthesis what would you  
like to do next<|im_end|>\n<|im_start|>user\ntell me about rational numbers<|im_end|>\n<|im_start|>assistant\nrational numbers are numbers that can be expressed as the ratio of two integers like a fraction  
they<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\ncan be written in the form ab where a and b are integers and b is not zero examples of rational numbers include 12 34
and<|im_end|>\n<|im_start|>user\nyeah", "room": "console"}
16:54:32.203 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.21375179290771484, "room": "console"}  
 16:54:32.205 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 12.08, "transcription_delay": 11.87, "room": "console"}  
 16:54:32.209 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:54:32.211 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:54:32.408 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.23, "prompt_tokens": 552, "prompt_cached_tokens": 0, "completion_tokens": 49,  
"tokens_per_second": 117.46, "room": "console"}  
 16:54:33.248 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "883f2745-ca95-4c0e-ae37-03cf6209f52e", "Date": "Sat, 31 Jan 2026 11:24:34  
GMT"}, "room": "console"}  
 16:54:33.983 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:54:33.985 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:54:35.263 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.3, "room": "console"}
16:54:38.179 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Nice.' → IGNORE {"room": "console"}
16:54:38.182 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Nice.' (backchannel ignored) {"room": "console"}  
 16:54:40.422 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7290125000000671, "audio_duration": 14.88, "room": "console"}
16:54:40.931 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.75, "room": "console"}
16:54:42.752 INFO … salescod…ntroller2 [DECISION] Exact phrase match in fillers: 'Wow.' → IGNORE {"room": "console"}
16:54:42.757 DEBUG… intelligent-agent [CLEARED-INTERIM] 'Wow.' (backchannel ignored) {"room": "console"}  
 16:54:46.894 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.05, "room": "console"}
16:54:46.897 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['stop'] → INTERRUPT {"room": "console"}
16:54:46.900 INFO … intelligent-agent [INTERRUPTED] 'Stop.' (command/real input detected) {"room": "console"}  
 16:54:46.902 DEBUG… livekit.agents received user transcript {"user_transcript": "Stop.", "language": "en", "transcript_delay": 9.079307317733765, "room": "console"}  
 16:54:46.912 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858686.912857 {"room": "console"}
16:54:46.915 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:54:46.917 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:54:47.108 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.016139540821313858, "duration": 0.196, "input": "<|im_start|>user\ntell me about rational numbers<|im_end|>\n<|im_start|>assistant\nrational  
numbers are numbers that can be expressed as the ratio of two integers like a fraction they<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\ncan be written in the form ab where a and b
are integers and b is not zero examples of rational numbers include 12 34 and<|im_end|>\n<|im_start|>user\nyeah stop", "room": "console"}
16:54:47.113 WARNI… livekit.agents preemptive generation enabled but chat context or tools have changed after `on_user_turn_completed` {"room": "console"}  
 16:54:47.115 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 9.29, "transcription_delay": 9.08, "room": "console"}  
 16:54:47.126 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:54:47.128 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}
16:54:47.405 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.22, "prompt_tokens": 607, "prompt_cached_tokens": 0, "completion_tokens": 22,  
"tokens_per_second": 76.86, "room": "console"}
16:54:48.093 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:54:48.095 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:54:50.339 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7507570000000214, "audio_duration": 5.56, "room": "console"}
16:54:52.182 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:54:53.658 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858693.6589208 {"room": "console"}
16:54:53.660 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:54:53.662 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:54:55.312 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.1, "room": "console"}
16:54:56.290 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.0, "room": "console"}
16:54:56.292 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Yeah.' → NO_DECISION {"room": "console"}  
 16:54:56.295 INFO … intelligent-agent [PROCESSING] 'Yeah.' (normal input, agent silent) {"room": "console"}
16:54:56.297 DEBUG… livekit.agents received user transcript {"user_transcript": "Yeah.", "language": "en", "room": "console"}  
 16:54:56.564 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.038619477301836014, "duration": 0.246, "input": "<|im_start|>assistant\ncan be written in the form ab where a and b are integers and b is not  
zero examples of rational numbers include 12 34 and<|im_end|>\n<|im_start|>user\nyeah<|im_end|>\n<|im_start|>assistant\neven whole numbers like 2 or 3 can be considered rational numbers because they can be  
written as 21 or 31 rational numbers can be added subtracted multiplied and divided<|im_end|>\n<|im_start|>user\nstop<|im_end|>\n<|im_start|>assistant\nwe were discussing rational numbers do you want to learn
more about it or move on to something else<|im_end|>\n<|im_start|>user\nyeah", "room": "console"}
16:54:56.636 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.21, "prompt_tokens": 640, "prompt_cached_tokens": 0, "completion_tokens": 29,  
"tokens_per_second": 86.47, "room": "console"}
16:54:56.802 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.5033020973205566, "room": "console"}
16:54:56.805 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.0, "transcription_delay": 0.0, "room": "console"}
16:54:56.809 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:54:56.811 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:54:56.879 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.6, "room": "console"}
16:54:57.276 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:54:57.278 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:55:00.164 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7489517000000205, "audio_duration": 6.92, "room": "console"}
16:55:00.495 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.6, "room": "console"}
16:55:02.478 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.0, "room": "console"}
16:55:04.260 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858704.260754 {"room": "console"}
16:55:04.262 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:55:04.264 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:55:05.784 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.3, "room": "console"}
16:55:06.124 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.4, "room": "console"}
16:55:06.779 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.6, "room": "console"}
16:55:06.782 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'Carry on.' → NO_DECISION {"room": "console"}
16:55:06.784 INFO … intelligent-agent [PROCESSING] 'Carry on.' (normal input, agent silent) {"room": "console"}  
 16:55:06.787 DEBUG… livekit.agents received user transcript {"user_transcript": "Carry on.", "language": "en", "transcript_delay": 0.466846227645874, "room": "console"}  
 16:55:07.104 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.4636611342430115, "duration": 0.271, "input": "<|im_start|>assistant\neven whole numbers like 2 or 3 can be considered rational numbers because
they can be written as 21 or 31 rational numbers can be added subtracted multiplied and divided<|im_end|>\n<|im_start|>user\nstop<|im_end|>\n<|im_start|>assistant\nwe were discussing rational numbers do you  
want to learn more about it or move on to something else<|im_end|>\n<|im_start|>user\nyeah<|im_end|>\n<|im_start|>assistant\ni'll stop here then what's next do you want to explore something new or pick up  
where we left off on rational numbers<|im_end|>\n<|im_start|>user\ncarry on", "room": "console"}
16:55:07.112 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.322859525680542, "room": "console"}  
 16:55:07.116 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.79, "transcription_delay": 0.47, "room": "console"}
16:55:07.130 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:55:07.132 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}
16:55:07.180 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.21, "prompt_tokens": 682, "prompt_cached_tokens": 0, "completion_tokens": 70,  
"tokens_per_second": 179.51, "room": "console"}
16:55:07.825 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:55:07.827 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:55:07.984 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.2, "room": "console"}
16:55:12.183 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.2, "room": "console"}
16:55:15.192 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['but'] → INTERRUPT {"room": "console"}
16:55:15.194 DEBUG… intelligent-agent [INTERRUPTED-INTERIM] 'Yeah. But' (command detected) {"room": "console"}
16:55:15.204 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858715.2042859 {"room": "console"}  
 16:55:15.205 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}  
 16:55:15.207 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:55:16.752 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.55, "room": "console"}
16:55:16.755 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['actually'] → INTERRUPT {"room": "console"}
16:55:16.757 INFO … intelligent-agent [INTERRUPTED] 'Actually,' (command/real input detected) {"room": "console"}  
 16:55:16.760 DEBUG… livekit.agents received user transcript {"user_transcript": "Actually,", "language": "en", "room": "console"}  
 16:55:17.012 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.007782121654599905, "duration": 0.244, "input": "<|im_start|>assistant\nwe were discussing rational numbers do you want to learn more about it
or move on to something else<|im_end|>\n<|im_start|>user\nyeah<|im_end|>\n<|im_start|>assistant\ni'll stop here then what's next do you want to explore something new or pick up where we left off on rational  
numbers<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nrational numbers have some important properties like they can be expressed as decimals
either<|im_end|>\n<|im_start|>user\nactually", "room": "console"}
16:55:17.082 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.23, "prompt_tokens": 711, "prompt_cached_tokens": 0, "completion_tokens": 22,  
"tokens_per_second": 69.68, "room": "console"}
16:55:18.025 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "3dd0b523-19ed-4f74-ab01-f45ecbdc1839", "Date": "Sat, 31 Jan 2026 11:25:19  
GMT"}, "room": "console"}
16:55:18.397 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'There is a' → NO_DECISION {"room": "console"}
16:55:18.399 DEBUG… intelligent-agent [PROCESSING-INTERIM] 'There is a' (normal input) {"room": "console"}
16:55:18.838 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 2.05, "room": "console"}
16:55:18.842 DEBUG… salescod…ntroller2 [DECISION] Agent silent: 'There is a problem.' → NO_DECISION {"room": "console"}
16:55:18.845 INFO … intelligent-agent [PROCESSING] 'There is a problem.' (normal input, agent silent) {"room": "console"}  
 16:55:18.848 DEBUG… livekit.agents received user transcript {"user_transcript": "There is a problem.", "language": "en", "transcript_delay": 0.7229962348937988, "room": "console"}  
 16:55:19.143 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.04733405262231827, "duration": 0.204, "input": "<|im_start|>assistant\nwe were discussing rational numbers do you want to learn more about it  
or move on to something else<|im_end|>\n<|im_start|>user\nyeah<|im_end|>\n<|im_start|>assistant\ni'll stop here then what's next do you want to explore something new or pick up where we left off on rational  
numbers<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nrational numbers have some important properties like they can be expressed as decimals
either<|im_end|>\n<|im_start|>user\nactually there is a problem", "room": "console"}
16:55:19.147 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.2942490577697754, "room": "console"}  
 16:55:19.150 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 1.02, "transcription_delay": 0.73, "room": "console"}  
 16:55:19.154 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}  
 16:55:19.156 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:55:19.172 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.24, "prompt_tokens": 716, "prompt_cached_tokens": 0, "completion_tokens": 22,  
"tokens_per_second": 70.49, "room": "console"}  
 16:55:20.107 DEBUG… livekit.….deepgram Established new Deepgram TTS WebSocket connection:  
 {"headers": {"dg-project-id": "5d94b310-8b03-408f-9b4a-dce7c4fda917", "dg-request-id": "969a5a46-bfa1-4393-90f9-dc4e1a281049", "Date": "Sat, 31 Jan 2026 11:25:21  
GMT"}, "room": "console"}  
 16:55:20.198 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 1.3, "room": "console"}
16:55:20.831 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:55:20.834 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}  
 16:55:20.898 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.7, "room": "console"}
16:55:22.825 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7187417000000096, "audio_duration": 5.12, "room": "console"}
16:55:25.903 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.0, "room": "console"}
16:55:25.956 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858725.95674 {"room": "console"}
16:55:25.958 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:55:25.961 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:55:26.700 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.8, "room": "console"}
16:55:26.702 INFO … salescod…ntroller2 [DECISION] Interrupt commands: ['sorry'] → INTERRUPT {"room": "console"}
16:55:26.704 INFO … intelligent-agent [INTERRUPTED] 'Sorry.' (command/real input detected) {"room": "console"}  
 16:55:26.706 DEBUG… livekit.agents received user transcript {"user_transcript": "Sorry.", "language": "en", "room": "console"}  
 16:55:26.942 DEBUG… livekit.…\_detector eou prediction  
 {"eou_probability": 0.01686950959265232, "duration": 0.22, "input": "<|im_start|>assistant\ni'll stop here then what's next do you want to explore something new or  
pick up where we left off on rational numbers<|im_end|>\n<|im_start|>user\ncarry on<|im_end|>\n<|im_start|>assistant\nrational numbers have some important properties like they can be expressed as decimals  
either<|im_end|>\n<|im_start|>user\nactually there is a problem<|im_end|>\n<|im_start|>assistant\nwhat seems to be the problem can you tell me more about it so i can try to
help<|im_end|>\n<|im_start|>user\nsorry", "room": "console"}
16:55:27.012 INFO … livekit.agents LLM metrics  
 {"model_name": "llama-3.3-70b-versatile", "model_provider": "api.groq.com", "ttft": 0.24, "prompt_tokens": 749, "prompt_cached_tokens": 0, "completion_tokens": 15,  
"tokens_per_second": 49.8, "room": "console"}  
 16:55:27.217 DEBUG… livekit.agents using preemptive generation {"preemptive_lead_time": 0.5081443786621094, "room": "console"}
16:55:27.219 INFO … livekit.agents EOU metrics {"model_name": "multilingual", "model_provider": "livekit", "end_of_utterance_delay": 0.0, "transcription_delay": 0.0, "room": "console"}  
 16:55:27.224 DEBUG… salescod…ntroller2 Agent state: listening → thinking {"room": "console"}
16:55:27.228 DEBUG… intelligent-agent [STATE] listening → thinking {"room": "console"}  
 16:55:27.748 DEBUG… salescod…ntroller2 Agent state: thinking → speaking {"room": "console"}
16:55:27.750 DEBUG… intelligent-agent [STATE] thinking → speaking {"room": "console"}
16:55:29.170 INFO … livekit.agents TTS metrics {"model_name": "aura-2-andromeda-en", "model_provider": "Deepgram", "ttfb": 0.7923405999999886, "audio_duration": 3.84, "room": "console"}
16:55:31.557 DEBUG… salescod…ntroller2 Agent stopped speaking at 1769858731.5574918 {"room": "console"}
16:55:31.559 DEBUG… salescod…ntroller2 Agent state: speaking → listening {"room": "console"}
16:55:31.561 DEBUG… intelligent-agent [STATE] speaking → listening {"room": "console"}  
 16:55:31.983 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 5.25, "room": "console"}
16:55:35.283 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 3.3, "room": "console"}
Exception in thread Thread-3 (\_listen_for_keys):
Traceback (most recent call last):
File "C:\Python312\Lib\threading.py", line 1073, in \_bootstrap_inner  
 self.run()
File "C:\Python312\Lib\threading.py", line 1010, in run  
 self.\_target(\*self.\_args, \*\*self.\_kwargs)  
 File "C:\Users\manav\Videos\liv\agents-assignment\venv\Lib\site-packages\livekit\agents\cli\cli.py", line 1246, in \_listen_for_keys  
 ch = readkey()
^^^^^^^^^
File "C:\Users\manav\Videos\liv\agents-assignment\venv\Lib\site-packages\livekit\agents\cli\readchar.py", line 250, in \_win_readkey  
 16:55:39.386 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 4.1, "room": "console"}  
 raise KeyboardInterrupt
KeyboardInterrupt  
 16:55:40.278 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.9, "room": "console"}
16:55:40.621 INFO … livekit.agents STT metrics {"model_name": "deepgram/nova-3", "model_provider": "livekit", "audio_duration": 0.4, "room": "console"}
16:55:41.868 INFO … livekit.agents shutting down worker {"id": "unregistered"}  
 16:55:43.894 DEBUG… livekit.agents session closed {"reason": "user_initiated", "error": null, "room": "console"}  
 16:55:43.936 DEBUG… livekit.agents shutting down job task {"reason": "", "user_initiated": false, "room": "console"}  
 16:55:43.946 INFO … intelligent-agent Session ended. Usage: UsageSummary(llm_prompt_tokens=8646, llm_prompt_cached_tokens=0, llm_input_audio_tokens=0, llm_input_cached_audio_tokens=0,  
 llm_input_text_tokens=0, llm_input_cached_text_tokens=0, llm_input_image_tokens=0, llm_input_cached_image_tokens=0, llm_completion_tokens=963,  
 llm_output_audio_tokens=0, llm_output_image_tokens=0, llm_output_text_tokens=0, tts_characters_count=1910, tts_audio_duration=129.8404583333333,  
 stt_audio_duration=230.4499999999997)  
 {"room": "console"}
16:55:43.951 DEBUG… livekit.agents job exiting {"reason": "", "tid": 24348, "job_id": "fake-job-ebf06e4844b7", "room_id": "FAKE_RM_3068cf45cb6f"}
16:55:43.954 INFO … intelligent-agent Controller stats: {'current_state': 'listening', 'ignore_words_count': 34, 'interrupt_words_count': 18, 'grace_period_seconds': 0.5, 'time_since_speaking':  
 12.396573305130005}  
 {"room": "console"}
16:55:43.971 DEBUG… livekit.agents http_session(): closing the httpclient ctx  
 16:55:43.998 INFO … livekit.agents process exiting {"reason": "", "pid": 25252, "inference": true}
(venv) PS C:\Users\manav\Videos\liv\agents-assignment\examples\voice_agents>
