import socket
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


class NetIO(IO):
    """Line-oriented TCP IO over a pair of binary file objects (rfile/wfile),
    as provided by socketserver.StreamRequestHandler. Used by the LAN server.

    - Output is encoded UTF-8 with \\r\\n line endings (telnet-friendly).
    - Input is decoded UTF-8 leniently; CR is stripped (handles both `nc` and
      `telnet` clients).
    - Socket timeouts and closed connections are surfaced as 'quit', which the
      session loop handles cleanly.
    """

    def __init__(self, rfile, wfile) -> None:
        self._rfile = rfile
        self._wfile = wfile

    def send(self, text: str) -> None:
        try:
            self._wfile.write((text + "\r\n").encode("utf-8", errors="replace"))
            self._wfile.flush()
        except (BrokenPipeError, OSError):
            # Player disconnected mid-output. The session loop will discover this
            # on the next receive().
            pass

    def receive(self, prompt: str = "> ") -> str:
        if prompt:
            try:
                self._wfile.write(prompt.encode("utf-8", errors="replace"))
                self._wfile.flush()
            except (BrokenPipeError, OSError):
                return "quit"
        try:
            line = self._rfile.readline()
        except (socket.timeout, TimeoutError):
            return "quit"
        except (ConnectionResetError, OSError):
            return "quit"
        if not line:
            return "quit"  # EOF on the socket
        return line.decode("utf-8", errors="replace").rstrip("\r\n").rstrip()


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
