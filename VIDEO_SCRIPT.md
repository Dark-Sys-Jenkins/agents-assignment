# Video Explanation Script: GenAI Engineer Assignment

## Introduction
Hello, I’m rajveer kumar, and I’m a candidate for the GenAI and Software Engineering role. Today, I’m excited to present my submission for the GenAI Engineer Campus assignment, where I’ve focused on significantly improving the natural flow of real-time conversational AI.

## Problem Statement
The core challenge I addressed involves how Voice Activity Detection, or VAD, handles interruptions. In many standard systems, the moment any sound is detected, the agent stops talking. This is a major issue because users often provide passive feedback like “yeah,” “ok,” or “hmm” just to acknowledge they are listening. When an agent treats these fillers as total interruptions, it causes a frustrating, robotic experience where the agent constantly “hiccups” or stops for no reason.

## Assignment Requirements
To solve this, the assignment required a system that remains silent over passive fillers while speaking, but stays perfectly responsive to the same words when silent. We also needed to ensure that actual commands like “stop” or “wait” work instantly, even when mixed with filler words, all while maintaining ultra-low latency.

## Solution Approach
My approach involved implementing a sophisticated logic layer directly into the local LiveKit Agent SDK. I developed a “Wait-and-Validate” strategy that essentially moves the interruption decision from the VAD layer to the STT transcription stream. Instead of stopping on raw noise, my implementation pauses for a fraction of a second to check the incoming text against a modular ignore list. If it identifies only fillers, the agent seamlessly continues its speech without the user even noticing a break.

## Modular Implementation
The solution is highly modular. All ignored phrases and model settings are abstracted into a dedicated configuration file, allowing for easy updates via environment variables. By leveraging state detection, the system knows exactly when the agent is speaking versus listening, so a “yeah” in a quiet moment is still processed as a valid response, but the same “yeah” mid-sentence is ignored.

## Scenario Examples
To see this in action, imagine the agent is reading a long historical passage. You can say “yeah” or “ok” every few seconds, and the agent will keep flowing naturally. But the moment you say “yeah, but stop,” the system detects the semantic keyword “stop” and cuts the audio immediately.

## Engineering Relevance
This project goes beyond simple bug fixing; it’s about the engineering nuances of Agentic AI. Handling real-time voice streams requires a deep understanding of production-level conversational flow and latency management. This work directly aligns with the goal of creating sophisticated, human-like AI agents that can handle complex, real-world interactions.

## Conclusion
I am eager to apply this engineering mindset to build scalable, real-time AI solutions and contribute to the team’s success. Thank you for the opportunity to demonstrate my approach to this challenge.
