import asyncio
import os
from collections.abc import Callable

from dotenv import load_dotenv
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.context.aggregator import ContextAggregator
from pipecat.llm.openai import OpenAILLMService
from pipecat.pipeline.component import Component, Message
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineParams, PipelineRunner, PipelineTask
from pipecat.services.cartesia import CartesiaTTSService
from pipecat.services.deepgram import DeepgramSTTService
from pipecat.transports.network.websocket_server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)

load_dotenv(override=True)


class AudioReceivedNotificationComponent(Component):
    """Component that sends notification when full audio is received.

    Triggers when STT endpointing is detected.
    """

    def __init__(self, transport: WebsocketServerTransport, get_notification_message: Callable):
        """Initialize the component.

        Args:
            transport: WebSocket transport for sending notifications
            get_notification_message: Function that returns the notification message
        """
        super().__init__()
        self.transport = transport
        self.last_session_id = None
        self.get_notification_message = get_notification_message

    async def process(self, message: Message) -> Message:
        """Process incoming messages and send notifications when full audio is received.

        Args:
            message: The message to process

        Returns:
            The unchanged message
        """
        # Check if this is an endpointing event (full audio received)
        if (
            message.audio is not None
            and message.text is None
            and message.is_endpointing
            and message.session_id != self.last_session_id
        ):
            # Send a notification that full audio was received
            notification = self.get_notification_message()
            await self.transport.send_json(message.session_id, notification)
            self.last_session_id = message.session_id

        return message


class WsBot:
    """WebSocket-based voice bot using Pipecat pipeline components for audio processing."""

    def __init__(
        self,
        url: str,
        port: int,
        prompt: str,
        send_audio_received_notification: Callable | None = None,
    ) -> None:
        """Initialize the WebSocket bot.

        Args:
            url: Host URL for the WebSocket server
            port: Port for the WebSocket server
            prompt: System prompt for the LLM
            send_audio_received_notification: Optional callback for audio notifications
        """
        self.transport = WebsocketServerTransport(
            host=url,
            port=port,
            params=WebsocketServerParams(
                audio_out_enabled=True,
                add_wav_header=True,
                vad_enabled=True,
                vad_analyzer=SileroVADAnalyzer(),
                vad_audio_passthrough=True,
                session_timeout=180,  # 3 minutes
            ),
        )
        # Set up STT service
        self.stt = DeepgramSTTService(api_key=os.getenv("DEEPGRAM_API_KEY"))

        # Create context aggregator to maintain conversation history
        self.context_aggregator = ContextAggregator()
        self.system_prompt = prompt
        self.send_audio_received_notification = send_audio_received_notification

        # Set up LLM service
        self.llm = OpenAILLMService(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="gpt-4",
            system_prompt=self.system_prompt,
            temperature=0.7,
        )

        # Set up TTS service
        self.tts = CartesiaTTSService(
            api_key=os.getenv("CARTESIA_API_KEY"),
            voice_id="71a7ad14-091c-4e8e-a314-022ece01c121",  # British Reading Lady
        )

    def get_notification_message(self):
        """Generate the notification message when audio is received.

        Returns:
            dict: A JSON-serializable notification message
        """
        return {"status": "received", "message": "Audio received and processing"}

    def get_pipeline(self):
        """Create and return the configured bot pipeline."""
        # Create audio received notification component
        audio_received_notification = (
            AudioReceivedNotificationComponent(
                transport=self.transport,
                get_notification_message=self.get_notification_message,
            )
            if self.send_audio_received_notification
            else None
        )

        # Create the pipeline
        pipeline_components = [
            self.transport.input(),  # Handle incoming audio
        ]

        # Conditionally add audio received notification component
        if self.send_audio_received_notification:
            pipeline_components.append(audio_received_notification)

        # Add remaining components
        pipeline_components.extend(
            [
                self.stt,  # Speech-to-text
                self.context_aggregator.user(),  # Manage user message history
                self.llm,  # Language model
                self.context_aggregator.assistant(),  # Manage bot message history
                self.tts,  # Text-to-speech
                self.transport.output(),  # Handle outgoing audio
            ]
        )

        return Pipeline(pipeline_components)

    async def run_bot(self):
        """Run the websocket bot pipeline asynchronously."""
        # Run the pipeline
        task = PipelineTask(
            self.get_pipeline(),
            params=PipelineParams(
                audio_in_sample_rate=16000,
                audio_out_sample_rate=16000,
                allow_interruptions=False,
                enable_metrics=True,
            ),
        )
        await PipelineRunner().run(task)

    def start(self):
        """Start the bot in the event loop."""
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.run_bot())
        except KeyboardInterrupt:
            print("Bot stopped by user")
        finally:
            loop.close()
