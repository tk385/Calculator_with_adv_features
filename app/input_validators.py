from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any
from app.calculator_config import CalculatorConfig
from app.exceptions import ValidationError

@dataclass
class InputValidator:
    @staticmethod
    def validate_number(value: Any, config: CalculatorConfig) -> Decimal:
        number = InputValidator._convert_to_decimal(value)
        InputValidator._check_within_limits(number, config.max_input_value)
        return number.normalize()

    @staticmethod
    def _convert_to_decimal(value: Any) -> Decimal:
        try:
            if isinstance(value, str):
                value = value.strip()
            return Decimal(str(value))
        except InvalidOperation as e:
            raise ValidationError(f"Invalid number format: {value}") from e

    @staticmethod
    def _check_within_limits(number: Decimal, max_value: Decimal) -> None:
        if abs(number) > max_value:
            raise ValidationError(f"Value exceeds maximum allowed: {max_value}")
