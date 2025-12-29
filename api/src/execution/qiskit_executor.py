"""Quantum circuit execution using Qiskit AerSimulator."""

import logging
import traceback
from typing import Dict

from qiskit import qasm3
from qiskit.qasm3 import QASM3ImporterError
from qiskit_aer import AerSimulator
from qiskit_aer.aererror import AerError

logger = logging.getLogger(__name__)


class QiskitExecutor:
    """
    Executes quantum circuits using Qiskit's AerSimulator.

    This class handles:
    - Parsing OpenQASM 3 circuit strings
    - Executing circuits with configurable shot count
    - Returning measurement results as counts dictionary

    Usage:
        executor = QiskitExecutor()
        counts = executor.execute(circuit_string="OPENQASM 3; qubit q; h q;", shots=1024)
        # Returns: {"0": 512, "1": 512}
    """

    def __init__(self):
        """Initialize the Qiskit executor with AerSimulator backend."""
        self.simulator = AerSimulator()
        logger.debug("QiskitExecutor initialized with AerSimulator")

    def parse_circuit(self, circuit_string: str):
        """
        Parse an OpenQASM 3 circuit string into a Qiskit QuantumCircuit.

        Args:
            circuit_string: OpenQASM 3 circuit definition

        Returns:
            QuantumCircuit: Parsed circuit object

        Raises:
            QASM3ImporterError: If circuit syntax is invalid
        """
        circuit = qasm3.loads(circuit_string)
        logger.debug(
            f"Circuit parsed: {circuit.num_qubits} qubits, "
            f"depth {circuit.depth()}"
        )
        return circuit

    def execute(self, circuit_string: str, shots: int = 1024) -> Dict[str, int]:
        """
        Execute a quantum circuit and return measurement results.

        This method:
        1. Parses the OpenQASM 3 circuit string
        2. Executes using AerSimulator with specified shots
        3. Returns measurement counts as dictionary

        Args:
            circuit_string: OpenQASM 3 circuit definition
            shots: Number of circuit executions (default: 1024)

        Returns:
            dict: Measurement counts, e.g., {"0": 512, "1": 512}

        Raises:
            QASM3ImporterError: If circuit parsing fails (invalid syntax, undefined gates)
            AerError: If circuit execution fails (memory errors, runtime errors)
            Exception: For unexpected errors during execution
        """
        try:
            # Parse circuit
            circuit = self.parse_circuit(circuit_string)

            # Log execution details
            logger.info(
                f"Executing circuit: {circuit.num_qubits} qubits, "
                f"depth {circuit.depth()}, {shots} shots"
            )

            # Execute circuit with simulator
            job = self.simulator.run(circuit, shots=shots)
            result = job.result()
            counts = result.get_counts()

            logger.info(
                f"Execution completed: {len(counts)} distinct outcomes, "
                f"{sum(counts.values())} total shots"
            )

            return counts

        except QASM3ImporterError as e:
            # Circuit parse errors: invalid syntax, undefined gates/qubits
            logger.error(
                f"Circuit parse error: {str(e)}",
                exc_info=True
            )
            logger.error(f"Full stack trace:\n{traceback.format_exc()}")
            raise

        except AerError as e:
            # Execution errors: memory allocation, invalid operations
            logger.error(
                f"Quantum circuit execution error: {str(e)}",
                exc_info=True
            )
            logger.error(f"Full stack trace:\n{traceback.format_exc()}")
            raise

        except MemoryError as e:
            # Explicit memory error handling (circuit too large)
            logger.error(
                f"Memory allocation failed during execution: {str(e)}",
                exc_info=True
            )
            logger.error(f"Full stack trace:\n{traceback.format_exc()}")
            raise

        except Exception as e:
            # Catch-all for unexpected errors
            logger.error(
                f"Unexpected error during circuit execution: {type(e).__name__}: {str(e)}",
                exc_info=True
            )
            logger.error(f"Full stack trace:\n{traceback.format_exc()}")
            raise
