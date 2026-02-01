from livekit.agents import metrics
from livekit.agents.voice import (
    AgentStateChangedEvent,
    MetricsCollectedEvent,
    UserInputTranscribedEvent,
)

from interrupt_controller import InterruptController


def register_metrics_handlers(session, usage_collector, logger) -> None:
    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)


def register_interrupt_handlers(
    session,
    interrupt_controller: InterruptController,
    logger,
) -> None:
    @session.on("agent_state_changed")
    def _on_agent_state_changed(ev: AgentStateChangedEvent):
        try:
            logger.debug("Agent state changed event: %s", ev.new_state)
            interrupt_controller.on_agent_state_changed(ev.new_state)
        except Exception:
            pass

    @session.on("speech_created")
    def _on_speech_created(ev):
        interrupt_controller.agent_is_speaking = True
        logger.info("Speech created → AgentSpeaking TRUE")

    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: UserInputTranscribedEvent):
        """
        This event fires only AFTER VAD detects speech.
        So this is our VAD signal.
        """
        logger.debug("User input transcribed event: %s", ev.transcript)
        # If agent is speaking, mark a pending interruption
        # Mark possible interruption ONLY if agent is speaking
        if interrupt_controller.agent_is_speaking and ev.is_final:
            interrupt_controller.on_user_speech_detected()

        text = ev.transcript or ""
        if not isinstance(text, str):
            text = str(text)

        if ev.is_final and interrupt_controller.should_interrupt(text):
            logger.info("Semantic interruption confirmed: %s", text)
            session.interrupt()
            return

        # We ONLY decide on final transcripts
        if not ev.is_final:
            return

        # Agent is silent → commit user turn so manual turn detection can respond
        if not interrupt_controller.agent_is_speaking:
            try:
                logger.info(
                    "AgentSpeaking : %s Committing user turn: %s",
                    interrupt_controller.agent_is_speaking,
                    text,
                )
                session.commit_user_turn()
            except Exception:
                logger.exception("Error committing user turn")
                session.commit_user_turn()


def create_usage_logger(ctx, usage_collector, logger) -> None:
    async def log_usage():
        try:
            summary = usage_collector.get_summary()
            logger.info(f"Usage: {summary}")
        except Exception as e:
            logger.error(f"Error logging usage: {e}")

    ctx.add_shutdown_callback(log_usage)
