from abc import ABC, abstractmethod


class IO(ABC):
    @abstractmethod
    def send(self, text: str) -> None: ...

    @abstractmethod
    def receive(self, prompt: str = "> ") -> str: ...


class LocalIO(IO):
    def send(self, text: str) -> None:
        print(text)

    def receive(self, prompt: str = "> ") -> str:
        try:
            return input(prompt)
        except EOFError:
            return "quit"


class ScriptedIO(IO):
    """Drives a session from a list of inputs. Records outputs. For tests."""

    def __init__(self, inputs: list[str]) -> None:
        self._inputs = iter(inputs)
        self.outputs: list[str] = []

    def send(self, text: str) -> None:
        self.outputs.append(text)

    def receive(self, prompt: str = "> ") -> str:
        try:
            return next(self._inputs)
        except StopIteration:
            return "quit"

    @property
    def transcript(self) -> str:
        return "\n".join(self.outputs)
