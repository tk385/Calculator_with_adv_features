from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Union
from dotenv import load_dotenv
import requests
import json
import os
import logging
import datetime

from app.exceptions import OperationError

# Load environment variables from .env file
load_dotenv()

# API Endpoint and API Key
API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
API_KEY = os.getenv("API_KEY") 

# Define functions for arithmetic operations
def add(a, b):
    return a + b

def subtract(a, b):
    return a - b

def multiply(a, b):
    return a * b

def divide(a, b):
    if b != 0:
        return a / b
    else:
        return "Error: Division by zero"

# Function to call the Groq API
def call_groq_function(prompt, functions, model="llama3-8b-8192"):
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "functions": functions,
        "function_call": "auto",
    }

    try:
        response = requests.post(API_ENDPOINT, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()

        # Check if the model called a function
        if "function_call" in data["choices"][0]["message"]:
            function_name = data["choices"][0]["message"]["function_call"]["name"]
            arguments = json.loads(data["choices"][0]["message"]["function_call"]["arguments"])
            return function_name, arguments

        return None, None

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return None, None

@dataclass
class Calculation:
    operation: str
    operand1: Decimal
    operand2: Decimal
    mode: str
    result: Decimal = field(init=False)
    timestamp: datetime.datetime = field(default_factory=datetime.datetime.now)

    def __post_init__(self):
        self.perform_calculation()

    def perform_calculation(self):
        if self.mode == 'groq':
            self.result = self.perform_groq_calculation()
        else:
            self.result = self.perform_standard_calculation()

    def perform_standard_calculation(self) -> Decimal:
        try:
            if self.operation == 'add':
                return self.operand1 + self.operand2
            elif self.operation == 'subtract':
                return self.operand1 - self.operand2
            elif self.operation == 'multiply':
                return self.operand1 * self.operand2
            elif self.operation == 'divide':
                return self.operand1 / self.operand2
            else:
                raise OperationError(f"Unsupported operation: {self.operation}")
        except InvalidOperation as e:
            logging.error(f"Invalid operation: {e}")
            raise OperationError(f"Invalid operation: {e}")

    def perform_groq_calculation(self) -> Decimal:
        logging.info("Performing calculation using Groq AI")
        functions = [
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
        ]

        prompt = f"Perform {self.operation} on {self.operand1} and {self.operand2}"
        function_name, arguments = call_groq_function(prompt, functions)

        if function_name and arguments:
            if function_name == "add":
                return Decimal(arguments["a"]) + Decimal(arguments["b"])
            elif function_name == "subtract":
                return Decimal(arguments["a"]) - Decimal(arguments["b"])
            elif function_name == "multiply":
                return Decimal(arguments["a"]) * Decimal(arguments["b"])
            elif function_name == "divide":
                result = divide(Decimal(arguments["a"]), Decimal(arguments["b"]))
                if isinstance(result, str): 
                    raise OperationError(result)
                return Decimal(result)
            else:
                raise OperationError("Error: Unknown function called")
        else:
            raise OperationError("No function call was made or an error occurred.")