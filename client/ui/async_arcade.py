"""Asyncio integration for Arcade game loop.

Allows running asyncio tasks alongside Arcade's game loop.
"""

import arcade
import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class AsyncArcadeScheduler:
    """
    Scheduler that integrates asyncio with Arcade's game loop.

    Allows async network operations to run alongside arcade.run().
    """

    def __init__(self):
        """Initialize the async scheduler."""
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.running = False

    def start(self):
        """Start the async scheduler."""
        if self.running:
            return

        # Get or create event loop
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)

        self.running = True
        logger.info("Async scheduler started")

    def stop(self):
        """Stop the async scheduler."""
        self.running = False
        logger.info("Async scheduler stopped")

    def update(self, delta_time: float):
        """
        Update function to be called from Arcade's on_update.

        Processes async tasks.

        Args:
            delta_time: Time since last update
        """
        if not self.running or not self.loop:
            return

        # Run pending async tasks for a short time
        # This allows network operations to progress
        try:
            # Create a short sleep task to allow I/O processing
            # This gives async tasks (including network I/O) time to progress
            async def tick():
                await asyncio.sleep(0)  # Yield control to let other tasks run
                await asyncio.sleep(0.001)  # Small delay to allow I/O

            # Run the tick, which processes I/O and ready callbacks
            self.loop.run_until_complete(tick())

        except Exception as e:
            logger.error(f"Error in async scheduler: {e}", exc_info=True)

    def create_task(self, coro):
        """
        Create an async task.

        Args:
            coro: Coroutine to run

        Returns:
            asyncio.Task
        """
        if not self.loop:
            self.start()

        return self.loop.create_task(coro)


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
    Schedule an async coroutine to run.

    Args:
        coro: Coroutine to run

    Returns:
        asyncio.Task
    """
    scheduler = get_async_scheduler()
    return scheduler.create_task(coro)


class AsyncWindow(arcade.Window):
    """
    Arcade Window with built-in asyncio support.

    Automatically runs async tasks alongside the game loop.
    """

    def __init__(self, *args, **kwargs):
        """Initialize async window."""
        super().__init__(*args, **kwargs)

        # Create async scheduler
        self.async_scheduler = AsyncArcadeScheduler()
        self.async_scheduler.start()

    def on_update(self, delta_time: float):
        """
        Update the window.

        Processes both game logic and async tasks.

        Args:
            delta_time: Time since last update
        """
        super().on_update(delta_time)

        # Process async tasks
        self.async_scheduler.update(delta_time)

    def close(self):
        """Close the window and stop async tasks."""
        self.async_scheduler.stop()
        super().close()


def run_with_asyncio():
    """
    Run arcade with asyncio integration.

    Use this instead of arcade.run() when you need async support.
    """
    # Get the asyncio event loop
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Start arcade
    # Arcade will handle the main loop
    arcade.run()

    # Clean up
    try:
        # Cancel remaining tasks
        pending = asyncio.all_tasks(loop)
        for task in pending:
            task.cancel()

        # Run until tasks are cancelled
        if pending:
            loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
    except Exception as e:
        logger.error(f"Error cleaning up async tasks: {e}")
    finally:
        loop.close()
