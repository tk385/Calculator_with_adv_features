from dataclasses import dataclass, field
import datetime
from decimal import Decimal, InvalidOperation
import logging
from typing import Any, Dict

from app.exceptions import OperationError


@dataclass
class Calculation:
    operation: str
    operand1: Decimal
    operand2: Decimal
    result: Decimal = field(init=False)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def __post_init__(self):
        self.result = self._perform_calculation()

    def _perform_calculation(self) -> Decimal:
        try:
            return self._apply_operation()
        except (InvalidOperation, ValueError, ArithmeticError) as e:
            raise OperationError(f"Calculation failed: {str(e)}")

    def _apply_operation(self) -> Decimal:
        operations = {
            "Addition": lambda x, y: x + y,
            "Subtraction": lambda x, y: x - y,
            "Multiplication": lambda x, y: x * y,
            "Division": lambda x, y: x / y if y != 0 else self._raise_error("Division by zero is not allowed"),
            "Power": lambda x, y: Decimal(pow(float(x), float(y))) if y >= 0 else self._raise_error("Negative exponents are not supported"),
            "Root": lambda x, y: Decimal(pow(float(x), 1/float(y))) if x >= 0 and y != 0 else self._raise_error("Invalid root operation"),
            "Average": lambda x, y: (x + y) / 2,
            "Mod": lambda x, y: x % y if y != 0 else self._raise_error("Division by zero is not allowed")
        }
        op = operations.get(self.operation)
        if not op:
            raise OperationError(f"Unknown operation: {self.operation}")
        return op(self.operand1, self.operand2)

    @staticmethod
    def _raise_error(message: str):
        raise OperationError(message)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'operation': self.operation,
            'operand1': str(self.operand1),
            'operand2': str(self.operand2),
            'result': str(self.result),
            'timestamp': self.timestamp.isoformat()
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> 'Calculation':
        try:
            calc = Calculation(
                operation=data['operation'],
                operand1=Decimal(data['operand1']),
                operand2=Decimal(data['operand2'])
            )
            calc.timestamp = datetime.datetime.fromisoformat(data['timestamp'])
            Calculation._validate_result(calc, Decimal(data['result']))
            return calc
        except (KeyError, InvalidOperation, ValueError) as e:
            raise OperationError(f"Invalid calculation data: {str(e)}")

    @staticmethod
    def _validate_result(calc, saved_result):
        if calc.result != saved_result:
            logging.warning(f"Loaded calculation result {saved_result} differs from computed result {calc.result}")

    def __str__(self) -> str:
        return f"{self.operation}({self.operand1}, {self.operand2}) = {self.result}"

    def __repr__(self) -> str:
        return (
            f"Calculation(operation='{self.operation}', "
            f"operand1={self.operand1}, "
            f"operand2={self.operand2}, "
            f"result={self.result}, "
            f"timestamp='{self.timestamp.isoformat()}')"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Calculation):
            return NotImplemented
        return (
            self.operation == other.operation and
            self.operand1 == other.operand1 and
            self.operand2 == other.operand2 and
            self.result == other.result
        )

    def format_result(self, precision: int = 10) -> str:
        try:
            return str(self.result.normalize().quantize(Decimal(f"1.{'0' * precision}")).normalize())
        except InvalidOperation:
            return str(self.result)
