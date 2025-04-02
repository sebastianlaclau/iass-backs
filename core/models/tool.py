from typing import Dict, Union, Literal
from .enums import ToolChoice

ToolChoiceType = Union[
    ToolChoice, Dict[Literal["type", "function"], Dict[Literal["name"], str]]
]
