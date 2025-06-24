from pathlib import Path
import json
import os # Not strictly needed if only using Path, but often useful with paths
import asyncio
from ..models.learning_models import LearningLogEntry
from loguru import logger

class LearningDataLoggerService:
    def __init__(self, log_file_path: Path = Path("learning_logs/events.jsonl")):
        self.log_file_path = log_file_path
        try:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"LearningDataLoggerService initialized. Logging to: {self.log_file_path.resolve()}")
        except Exception as e:
            # Log the error and re-raise to prevent the service from starting in a bad state
            logger.error(f"Failed to create directory for learning log {self.log_file_path}: {e}", exc_info=True)
            raise OSError(f"Could not create log directory {self.log_file_path.parent}: {e}")

    async def log_entry(self, entry: LearningLogEntry):
        """
        Asynchronously logs a LearningLogEntry to the configured JSONL file.
        """
        try:
            # Pydantic's model_dump_json() is efficient for serialization.
            # Adding a newline character for JSONL format.
            json_string_with_newline = entry.model_dump_json() + "\n"

            loop = asyncio.get_event_loop()
            # Run the synchronous file writing operation in an executor thread
            await loop.run_in_executor(None, self._write_log_sync, json_string_with_newline)

            logger.debug(f"Logged learning entry: ID {entry.log_id}, Type {entry.event_type}, Agent {entry.primary_agent_id or 'N/A'}")
        except Exception as e:
            # Catch potential errors from model_dump_json or during scheduling/execution in executor
            logger.error(f"Failed to prepare or schedule learning log entry for writing: {e}", exc_info=True)
            # Depending on policy, could re-raise or just log. For now, just logging.

    def _write_log_sync(self, json_string_with_newline: str):
        """
        Synchronous helper method to write a log string to the file.
        This method is intended to be run in an executor.
        """
        try:
            with open(self.log_file_path, "a", encoding='utf-8') as f: # Append mode, specify encoding
                f.write(json_string_with_newline)
        except IOError as e_io:
            logger.error(f"IOError writing to learning log {self.log_file_path}: {e_io}", exc_info=True)
            # This error occurs in the executor thread. Re-raising it here might not be directly
            # catchable by the caller of log_entry unless Future.exception() is checked.
            # For critical logging, a more robust error propagation or retry mechanism might be needed.
            # For this subtask, logging the error is the primary action.
            # Consider if specific IOErrors should lead to service unhealthiness or different handling.
            raise # Re-raise to allow executor to signal failure if caller is designed to handle it.
        except Exception as e_generic: # Catch any other unexpected errors during file write
            logger.error(f"Unexpected error writing to learning log {self.log_file_path}: {e_generic}", exc_info=True)
            raise
