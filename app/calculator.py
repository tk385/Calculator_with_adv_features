from dataclasses import dataclass, field
import datetime
from decimal import Decimal
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import pandas as pd

from app.calculation import Calculation
from app.calculator_config import CalculatorConfig
from app.exceptions import OperationError, ValidationError
from app.history import AutoSaveObserver, HistoryObserver, LoggingObserver
from app.input_validators import InputValidator
from app.operations import Operation, OperationFactory

Number = Union[int, float, Decimal]
CalculationResult = Union[Number, str]

@dataclass
class CalculatorMemento:
    history: List[Calculation]
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        return {'history': [calc.to_dict() for calc in self.history], 'timestamp': self.timestamp.isoformat()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CalculatorMemento':
        return cls(history=[Calculation.from_dict(calc) for calc in data['history']],
                   timestamp=datetime.datetime.fromisoformat(data['timestamp']))

class Calculator:
    def __init__(self, config: Optional[CalculatorConfig] = None):
        self.config = self._initialize_config(config)
        self.history: List[Calculation] = []
        self.operation_strategy: Optional[Operation] = None
        self.observers: List[HistoryObserver] = []
        self.undo_stack: List[CalculatorMemento] = []
        self.redo_stack: List[CalculatorMemento] = []
        self._initialize_calculator()

    def _initialize_config(self, config: Optional[CalculatorConfig]) -> CalculatorConfig:
        if config is None:
            current_file = Path(__file__)
            project_root = current_file.parent.parent
            config = CalculatorConfig(base_dir=project_root)
        config.validate()
        os.makedirs(config.log_dir, exist_ok=True)
        return config

    def _initialize_calculator(self):
        self._setup_logging()
        self._setup_directories()
        self._load_initial_history()
        logging.info("Calculator initialized with configuration")

    def _setup_logging(self):
        log_file = self.config.log_file.resolve()
        logging.basicConfig(filename=str(log_file), level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s', force=True)
        logging.info(f"Logging initialized at: {log_file}")

    def _setup_directories(self):
        self.config.history_dir.mkdir(parents=True, exist_ok=True)

    def _load_initial_history(self):
        try:
            self.load_history()
        except Exception as e:
            logging.warning(f"Could not load existing history: {e}")

    def add_observer(self, observer: HistoryObserver):
        self.observers.append(observer)
        logging.info(f"Added observer: {observer.__class__.__name__}")

    def remove_observer(self, observer: HistoryObserver):
        self.observers.remove(observer)
        logging.info(f"Removed observer: {observer.__class__.__name__}")

    def notify_observers(self, calculation: Calculation):
        for observer in self.observers:
            observer.update(calculation)

    def set_operation(self, operation: Operation):
        self.operation_strategy = operation
        logging.info(f"Set operation: {operation}")

    def perform_operation(self, a: Union[str, Number], b: Union[str, Number]) -> CalculationResult:
        self._validate_operation_set()
        validated_a, validated_b = self._validate_inputs(a, b)
        result = self.operation_strategy.execute(validated_a, validated_b)
        self._record_calculation(validated_a, validated_b, result)
        return result

    def _validate_operation_set(self):
        if not self.operation_strategy:
            raise OperationError("No operation set")

    def _validate_inputs(self, a: Union[str, Number], b: Union[str, Number]) -> (Number, Number): # type: ignore
        return (InputValidator.validate_number(a, self.config),
                InputValidator.validate_number(b, self.config))

    def _record_calculation(self, a: Number, b: Number, result: CalculationResult):
        calculation = Calculation(str(self.operation_strategy), a, b, result)
        self.undo_stack.append(CalculatorMemento(self.history.copy()))
        self.redo_stack.clear()
        self.history.append(calculation)
        self._trim_history()
        self.notify_observers(calculation)

    def _trim_history(self):
        if len(self.history) > self.config.max_history_size:
            self.history.pop(0)

    def save_history(self):
        try:
            self.config.history_dir.mkdir(parents=True, exist_ok=True)
            self._save_to_csv(self.history, self.config.history_file)
        except Exception as e:
            logging.error(f"Failed to save history: {e}")
            raise OperationError(f"Failed to save history: {e}")

    def _save_to_csv(self, history, file_path):
        data = [
        {
            'operation': str(calc.operation),
            'operand1': str(calc.operand1),
            'operand2': str(calc.operand2),
            'result': str(calc.result),
            'timestamp': calc.timestamp.isoformat() if isinstance(calc.timestamp, datetime.datetime) else str(calc.timestamp)
        }
        for calc in history
    ]
        pd.DataFrame(data).to_csv(file_path, index=False)
        logging.info(f"History saved successfully to {file_path}")


    def load_history(self):
        try:
            if self.config.history_file.exists():
                df = pd.read_csv(self.config.history_file)
                self.history = self._build_history_from_df(df) if not df.empty else []
                logging.info(f"Loaded {len(self.history)} calculations from history")
            else:
                logging.info("No history file found - starting with empty history")
        except Exception as e:
            logging.error(f"Failed to load history: {e}")
            raise OperationError(f"Failed to load history: {e}")

    def _build_history_from_df(self, df):
        return [Calculation.from_dict({'operation': row['operation'], 'operand1': row['operand1'],
                                       'operand2': row['operand2'], 'result': row['result'],
                                       'timestamp': row['timestamp']}) for _, row in df.iterrows()]

    def get_history_dataframe(self) -> pd.DataFrame:
        return pd.DataFrame([{'operation': str(calc.operation), 'operand1': str(calc.operand1),
                              'operand2': str(calc.operand2), 'result': str(calc.result),
                              'timestamp': calc.timestamp} for calc in self.history])

    def show_history(self) -> List[str]:
        return [f"{calc.operation}({calc.operand1}, {calc.operand2}) = {calc.result}" for calc in self.history]

    def clear_history(self):
        self.history.clear()
        self.undo_stack.clear()
        self.redo_stack.clear()
        logging.info("History cleared")

    def undo(self) -> bool:
        if not self.undo_stack:
            return False
        self.redo_stack.append(CalculatorMemento(self.history.copy()))
        self.history = self.undo_stack.pop().history.copy()
        return True

    def redo(self) -> bool:
        if not self.redo_stack:
            return False
        self.undo_stack.append(CalculatorMemento(self.history.copy()))
        self.history = self.redo_stack.pop().history.copy()
        return True

    def display_help(self):
        help_text = """
        Calculator Commands:
        ----------------------
        Basic Commands:
            add <a> <b>         Add two numbers
            subtract <a> <b>    Subtract two numbers
            multiply <a> <b>    Multiply two numbers
            divide <a> <b>      Divide two numbers
            mod <a> <b>         Mod of two numbers
            average <a> <b>     Average of two numbers

        Advanced Commands:
            undo                Undo the last operation
            redo                Redo the previously undone operation
            save                Save calculation history
            load                Load calculation history
            history             Displays history only after load command
            clear               Clear all history
            help                Show this help message
            exit                Exit the calculator

        Enter numbers for operations and follow prompts.
        """
        print(help_text)



def calculator_repl():
    try:
        calc = Calculator()
        calc.add_observer(LoggingObserver())
        calc.add_observer(AutoSaveObserver(calc))
        print("Calculator started. Type 'help' for commands.")
        
        while True:
            try:
                command = input("\nEnter command: ").lower().strip()
                
                if command in ['help', 'h']:
                    calc.display_help()
                    continue
                if command in ['exit', 'quit', 'q']:
                    try:
                        calc.save_history()
                        print("History saved successfully.")
                    except Exception as e:
                        print(f"Warning: Could not save history: {e}")
                    print("Goodbye!")
                    break
                if command in ['history', 'hist']:
                    history = calc.show_history()
                    if not history:
                        print("No calculations in history")
                    else:
                        print("\nCalculation History:")
                        for i, entry in enumerate(history, 1):
                            print(f"{i}. {entry}")
                    continue
                if command in ['clear', 'c']:
                    calc.clear_history()
                    print("History cleared")
                    continue
                if command == 'undo':
                    if calc.undo():
                        print("Operation undone")
                    else:
                        print("Nothing to undo")
                    continue
                if command == 'redo':
                    if calc.redo():
                        print("Operation redone")
                    else:
                        print("Nothing to redo")
                    continue
                if command == 'save':
                    try:
                        calc.save_history()
                        print("History saved successfully")
                    except Exception as e:
                        print(f"Error saving history: {e}")
                    continue
                if command == 'load':
                    try:
                        calc.load_history()
                        print("History loaded successfully")
                        print("Enter history to get the data")
                    except Exception as e:
                        print(f"Error loading history: {e}")
                    continue
                if command in ['add', 'subtract', 'multiply', 'divide', 'power', 'root',"mod","average"]:
                    try:
                        print("\nEnter numbers (or 'cancel' to abort):")
                        a = input("First number: ")
                        if a.lower() == 'cancel':
                            print("Operation cancelled")
                            continue
                        b = input("Second number: ")
                        if b.lower() == 'cancel':
                            print("Operation cancelled")
                            continue
                        operation = OperationFactory.create_operation(command)
                        calc.set_operation(operation)
                        result = calc.perform_operation(a, b)
                        if isinstance(result, Decimal):
                            result = result.normalize()
                        print(f"\nResult: {result:.0f}")
                    except (ValidationError, OperationError) as e:
                        print(f"Error: {e}")
                    except Exception as e:
                        print(f"Unexpected error: {e}")
                    continue
                print(f"Unknown command: '{command}'. Type 'help' for available commands.")
            except KeyboardInterrupt:
                print("\nOperation cancelled")
                continue
            except EOFError:
                print("\nInput terminated. Exiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
                continue
    except Exception as e:
        print(f"Fatal error: {e}")
        logging.error(f"Fatal error in calculator REPL: {e}")
        raise

# Run REPL
if __name__ == "__main__":
    calculator_repl()
