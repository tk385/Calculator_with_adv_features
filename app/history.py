from abc import ABC, abstractmethod
import logging
from typing import Any
from app.calculation import Calculation
import psycopg2

class HistoryObserver(ABC):
    
    @abstractmethod
    def update(self, calculation: Calculation) -> None:
        pass


class LoggingObserver(HistoryObserver):
    
    def update(self, calculation: Calculation) -> None:
        self._validate_calculation(calculation)
        self._log_calculation(calculation)

    @staticmethod
    def _validate_calculation(calculation: Calculation) -> None:
        if calculation is None:
            raise AttributeError("Calculation cannot be None")

    @staticmethod
    def _log_calculation(calculation: Calculation) -> None:
        logging.info(
            f"Calculation performed: {calculation.operation} "
            f"({calculation.operand1}, {calculation.operand2}) = "
            f"{calculation.result}"
        )


class AutoSaveObserver(HistoryObserver):
    
    def __init__(self, calculator: Any):
        self.calculator = self._validate_calculator(calculator)

    def update(self, calculation: Calculation) -> None:
        self._validate_calculation(calculation)
        self._auto_save_if_enabled()

    @staticmethod
    def _validate_calculator(calculator: Any) -> Any:
        if not hasattr(calculator, 'config') or not hasattr(calculator, 'save_history'):
            raise TypeError("Calculator must have 'config' and 'save_history' attributes")
        return calculator

    @staticmethod
    def _validate_calculation(calculation: Calculation) -> None:
        if calculation is None:
            raise AttributeError("Calculation cannot be None")

    def _auto_save_if_enabled(self) -> None:
        if self.calculator.config.auto_save:
            self.calculator.save_history()
            logging.info("History auto-saved")


class PostgresObserver(HistoryObserver):
    
    def __init__(self, db_url: str):
        self.db_url = db_url

    def update(self, calculation: Calculation) -> None:
        self._validate_calculation(calculation)
        self._save_to_postgres(calculation)

    @staticmethod
    def _validate_calculation(calculation: Calculation) -> None:
        if calculation is None:
            raise AttributeError("Calculation cannot be None")

    def _save_to_postgres(self, calculation: Calculation) -> None:
        try:
            conn = psycopg2.connect(self.db_url)
            cursor = conn.cursor()
            query = """
                INSERT INTO calculation_history (operation, operand1, operand2, result, timestamp)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """
            cursor.execute(query, (calculation.operation, calculation.operand1, calculation.operand2, calculation.result))
            conn.commit()
            logging.info("Calculation saved to PostgreSQL")
        except Exception as e:
            logging.error(f"Failed to save calculation to PostgreSQL: {e}")
        finally:
            cursor.close()
            conn.close()
