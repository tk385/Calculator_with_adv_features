from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging
import datetime
import os
import pandas as pd

from app.calculation import Calculation, add, subtract, multiply, divide, call_groq_function
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

    def set_operation(self, operation: str):
        self.operation_strategy = OperationFactory.create_operation(operation)
        logging.info(f"Set operation: {operation}")

    def perform_operation(self, a: Union[str, Number], b: Union[str, Number], mode: str = 'standard') -> CalculationResult:
        self._validate_operation_set()
        validated_a, validated_b = self._validate_inputs(a, b)
        operation_name = self.operation_strategy.__class__.__name__.lower()
        if operation_name == 'addition':
            operation_name = 'add'
        elif operation_name == 'subtraction':
            operation_name = 'subtract'
        elif operation_name == 'multiplication':
            operation_name = 'multiply'
        elif operation_name == 'division':
            operation_name = 'divide'
        elif operation_name == 'mod':
            operation_name = 'mod'
        elif operation_name == 'average':
            operation_name = 'average'
        elif operation_name == 'power':
            operation_name = 'power'
        elif operation_name == 'root':
            operation_name = 'root'
        calculation = Calculation(operation_name, validated_a, validated_b, mode)
        self._record_calculation(calculation)
        return calculation.result

    def _validate_operation_set(self):
        if not self.operation_strategy:
            raise OperationError("Operation not set")

    def _validate_inputs(self, a: Union[str, Number], b: Union[str, Number]) -> (Number, Number): # type: ignore
        return (InputValidator.validate_number(a, self.config),
                InputValidator.validate_number(b, self.config))

    def _record_calculation(self, calculation: Calculation):
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
import psycopg2
from psycopg2.extras import RealDictCursor
from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
import logging
import datetime
import os
import pandas as pd

from app.calculation import Calculation, add, subtract, multiply, divide, call_groq_function
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
        self._initialize_postgres()

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

    def _initialize_postgres(self):
        try:
            self.pg_conn = psycopg2.connect(
                dbname=self.config.pg_database,
                user=self.config.pg_user,
                password=self.config.pg_password,
                host=self.config.pg_host,
                port=self.config.pg_port
            )
            self.pg_cursor = self.pg_conn.cursor(cursor_factory=RealDictCursor)
            self._create_results_table()
            logging.info("PostgreSQL connection established and table initialized.")
        except Exception as e:
            logging.error(f"Failed to connect to PostgreSQL: {e}")
            raise OperationError(f"Failed to connect to PostgreSQL: {e}")

    def _create_results_table(self):
        create_table_query = """
        CREATE TABLE IF NOT EXISTS calculation_results (
            id SERIAL PRIMARY KEY,
            operation VARCHAR(50),
            operand1 VARCHAR(50),
            operand2 VARCHAR(50),
            result VARCHAR(50),
            timestamp TIMESTAMP
        );
        """
        self.pg_cursor.execute(create_table_query)
        self.pg_conn.commit()

    def _save_result_to_postgres(self, calculation: Calculation):
        try:
            insert_query = """
            INSERT INTO calculation_results (operation, operand1, operand2, result, timestamp)
            VALUES (%s, %s, %s, %s, %s);
            """
            self.pg_cursor.execute(insert_query, (
                str(calculation.operation),
                str(calculation.operand1),
                str(calculation.operand2),
                str(calculation.result),
                calculation.timestamp
            ))
            self.pg_conn.commit()
            logging.info("Result saved to PostgreSQL.")
        except Exception as e:
            logging.error(f"Failed to save result to PostgreSQL: {e}")

    def add_observer(self, observer: HistoryObserver):
        self.observers.append(observer)
        logging.info(f"Added observer: {observer.__class__.__name__}")

    def remove_observer(self, observer: HistoryObserver):
        self.observers.remove(observer)
        logging.info(f"Removed observer: {observer.__class__.__name__}")

    def notify_observers(self, calculation: Calculation):
        for observer in self.observers:
            observer.update(calculation)

    def set_operation(self, operation: str):
        self.operation_strategy = OperationFactory.create_operation(operation)
        logging.info(f"Set operation: {operation}")

    def perform_operation(self, a: Union[str, Number], b: Union[str, Number], mode: str = 'standard') -> CalculationResult:
        self._validate_operation_set()
        validated_a, validated_b = self._validate_inputs(a, b)
        operation_name = self.operation_strategy.__class__.__name__.lower()
        if operation_name == 'addition':
            operation_name = 'add'
        elif operation_name == 'subtraction':
            operation_name = 'subtract'
        elif operation_name == 'multiplication':
            operation_name = 'multiply'
        elif operation_name == 'division':
            operation_name = 'divide'
        calculation = Calculation(operation_name, validated_a, validated_b, mode)
        self._record_calculation(calculation)
        return calculation.result

    def _validate_operation_set(self):
        if not self.operation_strategy:
            raise OperationError("Operation not set")

    def _validate_inputs(self, a: Union[str, Number], b: Union[str, Number]) -> (Number, Number):
        return (InputValidator.validate_number(a, self.config),
                InputValidator.validate_number(b, self.config))

    def _record_calculation(self, calculation: Calculation):
        self.undo_stack.append(CalculatorMemento(self.history.copy()))
        self.redo_stack.clear()
        self.history.append(calculation)
        self._trim_history()
        self.notify_observers(calculation)
        self._save_result_to_postgres(calculation)

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

    def close_postgres_connection(self):
        try:
            self.pg_cursor.close()
            self.pg_conn.close()
            logging.info("PostgreSQL connection closed.")
        except Exception as e:
            logging.error(f"Failed to close PostgreSQL connection: {e}")

    # Ensure PostgreSQL connection is closed on exit
    def __del__(self):
        self.close_postgres_connection()

def calculator_repl():
    try:
        calc = Calculator()
        calc.add_observer(LoggingObserver())
        calc.add_observer(AutoSaveObserver(calc))
        print("Calculator started. Type 'help' for commands.")

        while True:
            try:
                mode = input("Enter mode (standard/groq): ").strip().lower()
                if mode in ["exit", "quit"]:
                    try:
                        calc.save_history()
                        print("History saved successfully.")
                    except Exception as e:
                        print(f"Warning: Could not save history: {e}")
                    print("Goodbye!")
                    break
                if mode == "help":
                    calc.display_help()
                    continue
                if mode not in ['standard', 'groq']:
                    print("Invalid mode. Please enter 'standard' or 'groq'.")
                    continue

                if mode == 'groq':
                    print("Welcome to the Groq Function Chat!")
                    print("You can ask the system to perform addition, subtraction, multiplication, or division.")
                    while True:
                        prompt = input("You: ").strip()
                        if prompt.lower() in ["exit", "quit"]:
                            print("Goodbye!")
                            break
                        function_name, arguments = call_groq_function(prompt, [
                            {
                                "name": "add",
                                "description": "Add two numbers.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "a": {"type": "number", "description": "The first number."},
                                        "b": {"type": "number", "description": "The second number."}
                                    },
                                    "required": ["a", "b"]
                                },
                            },
                            {
                                "name": "subtract",
                                "description": "Subtract two numbers.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "a": {"type": "number", "description": "The first number."},
                                        "b": {"type": "number", "description": "The second number."}
                                    },
                                    "required": ["a", "b"]
                                },
                            },
                            {
                                "name": "multiply",
                                "description": "Multiply two numbers.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "a": {"type": "number", "description": "The first number."},
                                        "b": {"type": "number", "description": "The second number."}
                                    },
                                    "required": ["a", "b"]
                                },
                            },
                            {
                                "name": "divide",
                                "description": "Divide two numbers.",
                                "parameters": {
                                    "type": "object",
                                    "properties": {
                                        "a": {"type": "number", "description": "The first number."},
                                        "b": {"type": "number", "description": "The second number."}
                                    },
                                    "required": ["a", "b"]
                                },
                            }
                        ])
                        if function_name and arguments:
                            if function_name == "add":
                                result = add(arguments["a"], arguments["b"])
                            elif function_name == "subtract":
                                result = subtract(arguments["a"], arguments["b"])
                            elif function_name == "multiply":
                                result = multiply(arguments["a"], arguments["b"])
                            elif function_name == "divide":
                                result = divide(arguments["a"], arguments["b"])
                            else:
                                result = "Error: Unknown function called"
                            print(f"Result: {result}")

                            
                        else:
                            print("No function call was made or an error occurred.")
                else:
                    command = input("Enter operation (add, subtract, multiply, divide, etc.): ").strip().lower()
                    if command in ["exit", "quit"]:
                        try:
                            calc.save_history()
                            print("History saved successfully.")
                        except Exception as e:
                            print(f"Warning: Could not save history: {e}")
                        print("Goodbye!")
                        break
                    if command == "help":
                        calc.display_help()
                        continue
                    if command not in ['add', 'subtract', 'multiply', 'divide', 'power', 'root', 'mod', 'average']:
                        print(f"Unknown command: '{command}'. Type 'help' for available commands.")
                        continue
                    a = input("Enter first operand: ").strip()
                    b = input("Enter second operand: ").strip()
                    calc.set_operation(command)
                    result = calc.perform_operation(a, b, mode)
                    print(f"\nResult: {result}")
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
