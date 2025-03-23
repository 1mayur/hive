import asyncio
from dataclasses import dataclass

from loguru import logger
from pipecat.frames.frames import (
    CancelFrame,
    EndFrame,
    Frame,
    FrameDirection,
    InputAudioRawFrame,
    OutputAudioRawFrame,
    StartFrame,
    TransportMessageFrame,
    TransportMessageUrgentFrame,
)
from pipecat.transports.base_input import BaseInputTransport
from pipecat.transports.base_output import BaseOutputTransport
from pipecat.transports.base_transport import BaseTransport


@dataclass
class AudioConfig:
    """Configuration class for audio parameters."""

    sample_rate: int = 16000
    num_channels: int = 1


class QueueInputTransport(BaseInputTransport):
    def __init__(
        self, transport: BaseTransport, queue: asyncio.Queue, audio_config: AudioConfig = None
    ):
        super().__init__()
        self._transport = transport
        self._queue = queue
        self._server_task = None
        self._stop_server_event = asyncio.Event()
        self._audio_config = audio_config or AudioConfig()

    async def start(self, frame: StartFrame):
        await super().start(frame)
        if not self._server_task:
            self._server_task = self.create_task(self._server_task_handler())

    async def _server_task_handler(self):
        try:
            while not self._stop_server_event.is_set():
                try:
                    # Use wait_for with a timeout to allow checking stop event periodically
                    frame = await asyncio.wait_for(self._queue.get(), timeout=0.1)
                    audio_frame = InputAudioRawFrame(
                        audio=frame,
                        sample_rate=self._audio_config.sample_rate,
                        num_channels=self._audio_config.num_channels,
                    )
                    # Process the frame
                    await self.process_frame(audio_frame)
                    # Mark task as done
                    self._queue.task_done()
                except asyncio.TimeoutError:
                    # On timeout, create and process an empty audio frame
                    empty_frame = InputAudioRawFrame(
                        audio=b"",
                        sample_rate=self._audio_config.sample_rate,
                        num_channels=self._audio_config.num_channels,
                    )
                    await self.process_frame(empty_frame)
                    # Timeout allows us to check stop_event regularly
                except Exception as e:
                    # Log error but continue processing
                    self.logger.error(f"Error processing queue item: {e}")
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            self.logger.debug("Queue processing task was cancelled")

        self.logger.debug("Queue processing stopped")
        # If we exit the loop normally, still wait for the stop event
        # This ensures we don't exit prematurely if the queue is empty
        await self._stop_server_event.wait()

    async def cleanup(self):
        await super().cleanup()
        await self._transport.cleanup()

    async def stop(self, frame: EndFrame):
        await super().stop(frame)
        self._stop_server_event.set()
        if self._server_task:
            await self.wait_for_task(self._server_task)
            self._server_task = None

    async def cancel(self, frame: CancelFrame):
        await super().cancel(frame)
        if self._server_task:
            await self.cancel_task(self._server_task)
            self._server_task = None


class QueueOutputTransport(BaseOutputTransport):
    def __init__(self, transport: BaseTransport, queue: asyncio.Queue, **kwargs):
        super().__init__(**kwargs)
        self._transport = transport
        self._queue = queue

    async def start(self, frame: StartFrame):
        await super().start(frame)

    async def cleanup(self):
        await super().cleanup()
        await self._transport.cleanup()

    async def process_frame(self, frame: Frame, direction: FrameDirection):
        await super().process_frame(frame, direction)

    async def send_message(self, frame: TransportMessageFrame | TransportMessageUrgentFrame):
        await self._write_frame(frame)

    async def write_raw_audio_frames(self, frames: bytes):
        frame = OutputAudioRawFrame(
            audio=frames,
            sample_rate=self.sample_rate,
            num_channels=self._params.audio_out_channels,
        )
        await self._write_frame(frame)

    async def _write_frame(self, frame: Frame):
        try:
            payload = await self._params.serializer.serialize(frame)
            if payload and self._websocket:
                await self._websocket.send(payload)
        except Exception as e:
            logger.error(f"{self} exception sending data: {e.__class__.__name__} ({e})")


class QueueTransport(BaseTransport):
    def __init__(
        self,
        input_queue: asyncio.Queue,
        output_queue: asyncio.Queue,
        input_name: str | None = None,
        output_name: str | None = None,
        audio_config: AudioConfig = None,
    ):
        super().__init__(input_name=input_name, output_name=output_name)
        self._input: QueueInputTransport | None = None
        self._output: QueueOutputTransport | None = None
        self._input_queue = input_queue
        self._output_queue = output_queue
        self._audio_config = audio_config or AudioConfig()

    def input(self) -> QueueInputTransport:
        if not self._input:
            self._input = QueueInputTransport(
                self, self._input_queue, audio_config=self._audio_config
            )
        return self._input

    def output(self) -> QueueOutputTransport:
        if not self._output:
            self._output = QueueOutputTransport(self._output_queue)
        return self._output
