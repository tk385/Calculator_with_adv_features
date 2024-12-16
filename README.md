# Calculator Program

This repository provides a feature-rich calculator program written in Python, designed to demonstrate principles of object-oriented programming (OOP), error handling, and software configuration. The calculator supports various arithmetic operations and is containerized for easy deployment.

---

## Features

- **Operations Supported**:
  - Addition, Subtraction, Multiplication, Division, Modulus, Average
  - Power, Root operations with error handling
- **Advanced Configuration**:
  - Customizable settings like precision, history size, and max input values, configured through environment variables or fallback defaults.
- **Persistence**:
  - Calculation history can be saved and loaded, with directories and file paths configured dynamically.
- **Validation & Error Handling**:
  - Input validation and descriptive error messages for invalid configurations and operations.

## Screenshots

<img width="278" alt="Screenshot 2024-11-09 at 9 22 32 AM" src="https://github.com/user-attachments/assets/1162375f-2569-4ebb-bbfc-482d25588e05">
<img width="294" alt="Screenshot 2024-11-09 at 9 22 41 AM" src="https://github.com/user-attachments/assets/32e82aa8-c118-473c-bc9d-4e217403acc3">
<img width="511" alt="Screenshot 2024-11-09 at 9 21 05 AM" src="https://github.com/user-attachments/assets/f7160130-e37b-437e-9f69-1acf202751a8">
<img width="518" alt="Screenshot 2024-11-09 at 9 21 16 AM" src="https://github.com/user-attachments/assets/cd364948-db12-4ce3-90bf-6463d012ffcc">
<img width="335" alt="Screenshot 2024-11-09 at 9 21 28 AM" src="https://github.com/user-attachments/assets/c500e86c-bf9d-4cf7-88ce-9e4c1e0a9e71">
<img width="628" alt="Screenshot 2024-11-09 at 9 21 37 AM" src="https://github.com/user-attachments/assets/4d49aabe-c19f-445c-86aa-85a157e8d3b4">
<img width="389" alt="Screenshot 2024-11-09 at 9 21 44 AM" src="https://github.com/user-attachments/assets/a717fee2-9395-4206-92bf-f5432a85730e">
<img width="376" alt="Screenshot 2024-11-09 at 9 21 59 AM" src="https://github.com/user-attachments/assets/096422e1-9c22-4683-9761-507a6b84fb43">
<img width="313" alt="Screenshot 2024-11-09 at 9 22 12 AM" src="https://github.com/user-attachments/assets/45bddd08-307e-4b05-b381-5fc948c0cc8f">



# Groq ai calculator

![alt text]("./groq.png")

# Postgress Sql

![alt text]("./postgress.png")


## Installation

0. Make sure your environment's python version is >= 3.10 to be able to run this :

   ```bash
   Download latest python version form here : https://www.python.org/downloads/
   ```

1. Clone this repository:

   ```bash
   git clone https://github.com/sashankpannala/Adv_caclulator_using_pandas.git
   cd Calculator_with_adv_features
   ```

2. Set up the virtual environment and install dependencies:

   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. To set up the environment variables, create a `.env` file in the project root:

   ```env
   CALCULATOR_BASE_DIR=/path/to/base/dir
   CALCULATOR_MAX_HISTORY_SIZE=100
   CALCULATOR_AUTO_SAVE=true
   CALCULATOR_PRECISION=10
   CALCULATOR_MAX_INPUT_VALUE=1e100
   CALCULATOR_DEFAULT_ENCODING=utf-8
   ```

4. Run the program:

   ```bash
   python3 main.py
   ```

## Usage

The calculator supports the following commands in its REPL interface:

- **Basic Operations**:
  - `add`, `subtract`, `multiply`, `divide`, `mod`, `average`
- **Advanced Operations**:
  - `power`, `root`
- **History Commands**:
  - `history` - Shows all past calculations
  - `clear` - Clears the calculation history
  - `undo`, `redo` - Undo/redo last operation
- **File Operations**:
  - `save`, `load` - Save/load calculation history to/from file
  - `exit` - Exit the calculator

## Configuration

The calculator's behavior can be customized through either environment variables or directly in the `CalculatorConfig` class. Available settings include:

- `CALCULATOR_BASE_DIR`: Base directory for saving logs and history files.
- `CALCULATOR_MAX_HISTORY_SIZE`: Maximum size of the calculation history.
- `CALCULATOR_AUTO_SAVE`: Automatically save history after each operation.
- `CALCULATOR_PRECISION`: Decimal precision of results.
- `CALCULATOR_MAX_INPUT_VALUE`: Maximum allowable input value.
- `CALCULATOR_DEFAULT_ENCODING`: Default encoding for files.

## Testing

To run the unit tests for this calculator:

```bash
pytest
```

Code coverage reports are generated and stored in the `htmlcov` directory.

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for more details.
