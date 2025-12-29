"""Qiskit startup validation for quantum circuit execution workers."""

import logging
import sys

logger = logging.getLogger(__name__)


def validate_qiskit() -> bool:
    """
    Validate Qiskit availability and functionality on worker startup.

    Returns:
        bool: True if validation successful, False otherwise.

    Exit Behavior:
        - On success: Returns True, worker proceeds to consume messages
        - On failure: Logs error to stderr and returns False
    """
    try:
        # Import Qiskit core modules
        from qiskit import __version__, qasm3
        from qiskit_aer import AerSimulator

        # Test basic functionality with minimal circuit
        test_circuit = qasm3.loads("OPENQASM 3; qubit q;")
        simulator = AerSimulator()

        # Log success with version info
        logger.info(f"Qiskit validation successful: version {__version__}")
        logger.info("Qiskit AerSimulator backend available")

        return True

    except ImportError as e:
        logger.error(f"FATAL: Qiskit import failed: {e}")
        return False

    except Exception as e:
        logger.error(f"FATAL: Qiskit validation failed: {e}")
        return False
