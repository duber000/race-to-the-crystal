"""Asyncio integration for Arcade game loop.

Allows running asyncio tasks alongside Arcade's game loop using threading.
"""

import arcade
import asyncio
import threading
import logging
from typing import Optional, Callable, Any
from queue import Queue
import pyglet.clock

logger = logging.getLogger(__name__)


class AsyncArcadeScheduler:
    """
    Scheduler that integrates asyncio with Arcade's game loop using threading.

    Runs asyncio event loop in a separate thread, allowing async network
    operations to run alongside Arcade's synchronous game loop without blocking.
    """

    def __init__(self):
        """Initialize the async scheduler."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False

    def start(self):
        """Start the async scheduler in a separate thread."""
        if self.running:
            logger.info("Async scheduler already running")
            return

        # Create a new event loop for the background thread
        self.loop = asyncio.new_event_loop()

        # Start the event loop in a daemon thread
        self.thread = threading.Thread(
            target=self._run_event_loop,
            name="AsyncArcadeScheduler",
            daemon=True
        )
        self.thread.start()

        self.running = True
        logger.info(f"Async scheduler started in thread {self.thread.name}")

    def _run_event_loop(self):
        """Run the event loop in the background thread."""
        asyncio.set_event_loop(self.loop)
        logger.info(f"Event loop running in thread {threading.current_thread().name}")
        try:
            self.loop.run_forever()
        except Exception as e:
            logger.error(f"Error in event loop thread: {e}", exc_info=True)
        finally:
            self.loop.close()
            logger.info("Event loop closed")

    def stop(self):
        """Stop the async scheduler."""
        if not self.running:
            return

        self.running = False

        if self.loop:
            # Stop the event loop from the background thread
            self.loop.call_soon_threadsafe(self.loop.stop)

        if self.thread and self.thread.is_alive():
            # Wait for thread to finish (with timeout)
            self.thread.join(timeout=2.0)

        logger.info("Async scheduler stopped")

    def update(self, delta_time: float):
        """
        Update function to be called from Arcade's on_update.

        With the threading approach, this is a no-op since the event loop
        runs independently in its own thread.

        Args:
            delta_time: Time since last update
        """
        # No-op: The event loop runs independently in its thread
        pass

    def create_task(self, coro):
        """
        Create an async task in the background event loop.

        This is thread-safe and can be called from Arcade's main thread.

        Args:
            coro: Coroutine to run

        Returns:
            asyncio.Task
        """
        if not self.running or not self.loop:
            logger.warning("Scheduler not running, starting now...")
            self.start()

        logger.debug(f"Scheduling coroutine from thread {threading.current_thread().name}: {coro}")

        # Use asyncio.run_coroutine_threadsafe for thread-safe task creation
        future = asyncio.run_coroutine_threadsafe(coro, self.loop)

        logger.debug(f"Task scheduled: {future}")
        return future


# Global scheduler instance
_scheduler: Optional[AsyncArcadeScheduler] = None


def get_async_scheduler() -> AsyncArcadeScheduler:
    """
    Get the global async scheduler instance.

    Returns:
        AsyncArcadeScheduler instance
    """
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncArcadeScheduler()
    return _scheduler


def schedule_async(coro):
    """
    Schedule an async coroutine to run in the background event loop.

    This is thread-safe and can be called from Arcade's main thread.

    Args:
        coro: Coroutine to run

    Returns:
        concurrent.futures.Future wrapping the task
    """
    logger.debug(f"schedule_async called with: {coro}")
    scheduler = get_async_scheduler()
    future = scheduler.create_task(coro)
    logger.debug(f"schedule_async returning future: {future}")
    return future


class AsyncWindow(arcade.Window):
    """
    Arcade Window with built-in asyncio support via threading.

    Starts an asyncio event loop in a background thread when first needed,
    allowing async tasks to run alongside the game loop without blocking.
    """

    def __init__(self, *args, **kwargs):
        """Initialize async window."""
        super().__init__(*args, **kwargs)

        # Use the global async scheduler (shared with schedule_async)
        # Don't start it immediately - wait until it's actually needed
        # This prevents interference with OpenGL context initialization
        self.async_scheduler = get_async_scheduler()
        logger.info(f"AsyncWindow initialized (scheduler will start on demand)")

    def on_update(self, delta_time: float):
        """
        Update the window.

        Args:
            delta_time: Time since last update
        """
        super().on_update(delta_time)

        # No need to manually update the scheduler - it runs in its own thread
        # This call is a no-op but kept for compatibility
        self.async_scheduler.update(delta_time)

    def close(self):
        """Close the window and stop async tasks."""
        self.async_scheduler.stop()
        super().close()


# Global queue for UI updates from background threads
_ui_update_queue: Queue = Queue()
_queue_processor_scheduled = False


def schedule_on_main_thread(callback: Callable, *args, **kwargs):
    """
    Schedule a callback to run on Arcade's main thread at a safe time.

    Use this when you need to update UI elements from an async context
    (background thread). OpenGL operations must happen on the main thread.

    This queues the callback and processes it during the update phase
    (between frames), not during draw operations, preventing OpenGL errors.

    Args:
        callback: Function to call on main thread
        *args: Positional arguments for callback
        **kwargs: Keyword arguments for callback
    """
    global _queue_processor_scheduled

    # Add callback to queue (thread-safe)
    _ui_update_queue.put((callback, args, kwargs))
    logger.debug(f"Queued {callback.__name__} for main thread execution")

    # Ensure processor is scheduled (only schedule once)
    if not _queue_processor_scheduled:
        _queue_processor_scheduled = True
        # Schedule processor to run on next update cycle
        pyglet.clock.schedule_interval(_process_ui_update_queue, 1/60)


def _process_ui_update_queue(delta_time: float):
    """
    Process queued UI updates on the main thread.

    This runs during the update phase, safely between draw operations.
    """
    # Process all queued updates
    while not _ui_update_queue.empty():
        try:
            callback, args, kwargs = _ui_update_queue.get_nowait()
            callback(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error processing queued UI update: {e}", exc_info=True)


def run_with_asyncio():
    """
    Run arcade with asyncio integration.

    With the threading approach, this is just an alias for arcade.run()
    since the async event loop runs in a separate thread.
    """
    # The async scheduler runs in its own thread, so just run arcade normally
    arcade.run()
