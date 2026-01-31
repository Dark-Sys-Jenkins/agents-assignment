from __future__ import annotations

import os
from opentelemetry.trace import Span
from ..tokenize.basic import split_words
from ..log import logger

from livekit import rtc

from ..telemetry import trace_types

def _parse_simple_yaml_list(lines: list[str], key: str) -> list[str]:
    """Manually parse a list of strings from a simple YAML structure without PyYAML."""
    items = []
    in_section = False
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith(f"{key}:"):
            in_section = True
            continue

        if in_section:
            if line.endswith(":") and not line.startswith("-"):
                # New section started
                break
            if line.startswith("-"):
                val = line.lstrip("- ").strip()
                if val:
                    items.append(val)
    return items

def _load_config_words(key: str) -> set[str]:
    try:
        current_dir = os.getcwd()
        # Look for config.yaml in current dir and up to root
        while True:
            config_path = os.path.join(current_dir, "config.yaml")
            if os.path.exists(config_path):
                logger.info(f"Loading {key} from {config_path}")
                with open(config_path, "r") as f:
                    lines = f.readlines()
                    words = _parse_simple_yaml_list(lines, key)
                    if words:
                        return set(w.lower() for w in words)
                break # Found file but maybe empty list, stop searching

            parent = os.path.dirname(current_dir)
            if parent == current_dir:
                break
            current_dir = parent

    except Exception as e:
        logger.warning(f"failed to load {key} from config.yaml", exc_info=e)

    logger.warning(f"No configuration found for {key} in config.yaml. Using empty set.")
    return set()


INTENT_WORDS = _load_config_words("intent_words")
BACKCHANNEL_WORDS = _load_config_words("backchannel_words")


def _set_participant_attributes(span: Span, participant: rtc.Participant) -> None:
    span.set_attributes(
        {
            trace_types.ATTR_PARTICIPANT_ID: participant.sid,
            trace_types.ATTR_PARTICIPANT_IDENTITY: participant.identity,
            trace_types.ATTR_PARTICIPANT_KIND: rtc.ParticipantKind.Name(participant.kind),
        }
    )

def _is_only_backchannels(text: str) -> bool:
    """Check if transcript consists only of backchannel words."""
    words = split_words(text.lower(), split_character=True)
    if not words:
        return False

    # split_words returns list of tuples (word, start_pos, end_pos)
    # Extract just the word text and normalize
    normalized_words = [w[0].strip().rstrip(".!?,;:") for w in words]

    # Check if ALL words are backchannels
    return all(word in BACKCHANNEL_WORDS for word in normalized_words if word)