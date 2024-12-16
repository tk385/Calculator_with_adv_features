from dataclasses import dataclass, field
from decimal import Decimal
from pathlib import Path
import os
from typing import Optional
from dotenv import load_dotenv

from app.exceptions import ConfigurationError

load_dotenv()

def get_project_root() -> Path:
    current_file = Path(__file__)
    return current_file.parent.parent

@dataclass
class CalculatorConfig:
    base_dir: Path = field(default_factory=lambda: Path(os.getenv('CALCULATOR_BASE_DIR', str(get_project_root()))).resolve())
    max_history_size: int = field(default_factory=lambda: int(os.getenv('CALCULATOR_MAX_HISTORY_SIZE', '1000')))
    precision: int = field(default_factory=lambda: int(os.getenv('CALCULATOR_PRECISION', '10')))
    max_input_value: Decimal = field(default_factory=lambda: Decimal(os.getenv('CALCULATOR_MAX_INPUT_VALUE', '1e999')))
    default_encoding: str = field(default_factory=lambda: os.getenv('CALCULATOR_DEFAULT_ENCODING', 'utf-8'))
    auto_save: Optional[bool] = None

    # PostgreSQL Configuration
    pg_database: str = field(default_factory=lambda: os.getenv("PG_DATABASE", "calculator_db"))
    pg_user: str = field(default_factory=lambda: os.getenv("PG_USER", "postgres"))
    pg_password: str = field(default_factory=lambda: os.getenv("PG_PASSWORD", "password"))
    pg_host: str = field(default_factory=lambda: os.getenv("PG_HOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("PG_PORT", "5432")))

    def __post_init__(self):
        if self.auto_save is None: 
            auto_save_env = os.getenv('CALCULATOR_AUTO_SAVE', 'true').strip().lower()
            self.auto_save = auto_save_env in ['true', '1']

    @property
    def log_dir(self) -> Path:
        return Path(os.getenv('CALCULATOR_LOG_DIR', str(self.base_dir / "logs"))).resolve()

    @property
    def history_dir(self) -> Path:
        return Path(os.getenv('CALCULATOR_HISTORY_DIR', str(self.base_dir / "history"))).resolve()

    @property
    def history_file(self) -> Path:
        return Path(os.getenv('CALCULATOR_HISTORY_FILE', str(self.history_dir / "calculator_history.csv"))).resolve()

    @property
    def log_file(self) -> Path:
        return Path(os.getenv('CALCULATOR_LOG_FILE', str(self.log_dir / "calculator.log"))).resolve()

    def validate(self) -> None:
        if self.max_history_size <= 0:
            raise ConfigurationError("max_history_size must be positive")
        if self.precision <= 0:
            raise ConfigurationError("precision must be positive")
        if self.max_input_value <= 0:
            raise ConfigurationError("max_input_value must be positive")
        if not all([self.pg_database, self.pg_user, self.pg_password]):
            raise ConfigurationError("PostgreSQL configuration is incomplete")
