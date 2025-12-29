"""Format Qiskit execution results for database storage."""

import logging

logger = logging.getLogger(__name__)


class ResultFormatter:
    """
    Formats Qiskit measurement results for database storage.

    This class converts Qiskit's counts dictionary to the JSONB format
    defined in RESULT_FORMAT.md. Since Qiskit's get_counts() already
    returns the correct format, this class primarily validates and
    logs the results.

    Usage:
        formatter = ResultFormatter()
        db_result = formatter.format_counts(counts={"0": 512, "1": 512})
        # Returns: {"0": 512, "1": 512} (validated)
    """

    @staticmethod
    def format_counts(counts: dict[str, int]) -> dict[str, int]:
        """
        Format Qiskit counts dictionary for database storage.

        Qiskit's result.get_counts() already returns the correct format:
        - Keys: Bitstrings (e.g., "00", "01", "10", "11")
        - Values: Integer counts

        This method validates the format and returns it unchanged.

        Args:
            counts: Qiskit measurement counts dictionary

        Returns:
            dict: Same dictionary, validated for database storage

        Raises:
            ValueError: If counts dictionary has invalid format
        """
        # Validate counts format
        if not isinstance(counts, dict):
            raise ValueError(f"Counts must be dict, got {type(counts)}")

        # Validate all keys are bitstrings
        for key in counts.keys():
            if not isinstance(key, str):
                raise ValueError(f"Count key must be string, got {type(key)}")
            if not all(c in '01' for c in key):
                raise ValueError(f"Count key must be bitstring, got '{key}'")

        # Validate all values are non-negative integers
        for value in counts.values():
            if not isinstance(value, int):
                raise ValueError(f"Count value must be int, got {type(value)}")
            if value < 0:
                raise ValueError(f"Count value must be non-negative, got {value}")

        logger.debug(
            f"Counts validated: {len(counts)} states, "
            f"{sum(counts.values())} total measurements"
        )

        # Return unchanged (Qiskit format matches database format)
        return counts

    @staticmethod
    def format_error(error: Exception, error_category: str = "Unexpected error") -> str:
        """
        Format an exception into a structured error message.

        Creates error messages with consistent format:
        "{error_category}: {exception_type}: {error_details}"

        Args:
            error: The exception that occurred
            error_category: Error category prefix (e.g., "Circuit parse error")

        Returns:
            str: Formatted error message for database storage

        Examples:
            >>> format_error(QASM3ImporterError("undefined gate"), "Circuit parse error")
            "Circuit parse error: QASM3ImporterError: undefined gate"
        """
        error_type = type(error).__name__
        error_message = str(error)

        formatted = f"{error_category}: {error_type}: {error_message}"

        logger.debug(f"Error formatted: {formatted}")

        return formatted
