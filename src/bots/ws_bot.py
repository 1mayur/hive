import asyncio
import os
from typing import Callable

from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.context.aggregator import ContextAggregator
from pipecat.llm.openai import OpenAILLMService
from pipecat.pipeline.component import Component, Message
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner, PipelineTask
from pipecat.rtvi.components import (
    RTVIBotTranscriptionService,
    RTVISpeakingService,
    RTVIUserTranscriptionService,
)
from pipecat.stt.openai import OpenAISTTService
from pipecat.transports.network.websocket_server import (
    WebsocketServerParams,
    WebsocketServerTransport,
)
from pipecat.tts.openai import OpenAITTSService


class AudioReceivedNotificationComponent(Component):
    """Component that sends notification when full audio is received and STT endpointing is triggered"""

    def __init__(
        self, transport: WebsocketServerTransport, get_notification_message: Callable
    ):
        super().__init__()
        self.transport = transport
        self.last_session_id = None
        self.get_notification_message = get_notification_message

    async def process(self, message: Message) -> Message:
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
    def __init__(
        self,
        url: str,
        port: int,
        prompt: str,
        send_audio_received_notification: Callable | None = None,
    ) -> None:
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
        self.stt = OpenAISTTService(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="whisper-1",
        )

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
        self.tts = OpenAITTSService(
            api_key=os.environ.get("OPENAI_API_KEY"),
            voice="alloy",
        )

    def get_pipeline(self):
        # Setup RTVI components
        rtvi_speaking = RTVISpeakingService()
        rtvi_user_transcription = RTVIUserTranscriptionService()
        rtvi_bot_transcription = RTVIBotTranscriptionService()

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
                self.context_aggregator.user(),     # Manage user message history
                self.stt,                           # Speech-to-text
                self.llm,                           # Language model
                self.context_aggregator.bot(),      # Manage bot message history
                rtvi_speaking,                      # Track speaking states
                rtvi_user_transcription,            # Handle user speech transcription
                rtvi_bot_transcription,             # Handle bot speech transcription
                self.tts,                           # Text-to-speech
                self.transport.output(),            # Handle outgoing audio
            ]
        )

        return Pipeline(pipeline_components)

    async def run_bot(self):
        # Run the pipeline
        task = PipelineTask(self.get_pipeline())
        await PipelineRunner().run(task)

    def start(self):
        """Start the bot in the event loop"""
        loop = asyncio.get_event_loop()
        try:
            loop.run_until_complete(self.run_bot())
        except KeyboardInterrupt:
            print("Bot stopped by user")
        finally:
            loop.close()
