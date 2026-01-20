"""
Asynchronous NLP analyzer for semantic analysis.

This module provides non-blocking semantic analysis for logging and research.
It does NOT block the real-time decision path.
"""

import asyncio
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SemanticAnalysis:
    """
    Results from semantic analysis of a user transcript.
    """

    intent: str  # "BACKCHANNEL", "COMMAND", "MIXED"
    has_discourse_marker: bool
    discourse_markers_found: set[str]
    confidence: float
    transcript: str


class NLPAnalyzer:
    """
    Asynchronous semantic analyzer for logging and research.

    This analyzer runs in the background and does NOT block audio playback.
    It provides additional intelligence beyond simple rule-based filtering.

    Features:
    - Discourse marker detection ("but", "however", "actually")
    - Intent classification
    - Confidence scoring (placeholder for future ML models)
    """

    # Discourse markers that often indicate topic shifts or interruptions
    DISCOURSE_MARKERS = {
        "but",
        "however",
        "actually",
        "although",
        "though",
        "except",
        "besides",
        "meanwhile",
        "instead",
        "on the other hand",
        "in fact",
        "nevertheless",
    }

    async def analyze(
        self,
        transcript: str,
        decision_was_ignore: bool,
    ) -> SemanticAnalysis:
        """
        Perform lightweight NLP analysis asynchronously.

        This runs async and doesn't block audio playback. Results are logged
        for observability and can be used for future improvements.

        Args:
            transcript: The user's transcribed speech
            decision_was_ignore: Whether the real-time filter decided to ignore

        Returns:
            SemanticAnalysis object with analysis results
        """
        # Simulate async processing (could be replaced with actual NLP model)
        await asyncio.sleep(0.001)

        tokens = transcript.lower().split()

        # Check for discourse markers
        markers_found = {
            marker for marker in self.DISCOURSE_MARKERS if marker in transcript.lower()
        }
        has_discourse = len(markers_found) > 0

        # Simple intent classification
        if has_discourse:
            intent = "MIXED"
        elif decision_was_ignore:
            intent = "BACKCHANNEL"
        else:
            intent = "COMMAND"

        # Placeholder confidence (could be from ML model)
        confidence = 0.85 if intent != "MIXED" else 0.7

        # Log for observability
        logger.info(
            f"📊 NLP Analysis: intent={intent}, "
            f"discourse_markers={markers_found}, "
            f"transcript='{transcript}'"
        )

        return SemanticAnalysis(
            intent=intent,
            has_discourse_marker=has_discourse,
            discourse_markers_found=markers_found,
            confidence=confidence,
            transcript=transcript,
        )

    async def batch_analyze(
        self, transcripts: list[tuple[str, bool]]
    ) -> list[SemanticAnalysis]:
        """
        Analyze multiple transcripts in batch.

        Args:
            transcripts: List of (transcript, decision_was_ignore) tuples

        Returns:
            List of SemanticAnalysis results
        """
        tasks = [self.analyze(t, d) for t, d in transcripts]
        return await asyncio.gather(*tasks)
