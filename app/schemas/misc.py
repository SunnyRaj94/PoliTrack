# app/schemas/misc.py
from pydantic import BaseModel


class Message(BaseModel):
    """
    A simple schema for returning a message in an API response.
    """

    message: str
