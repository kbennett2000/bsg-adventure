import queue
import socket
import threading
from abc import ABC, abstractmethod
from typing import Optional


class Disconnected(Exception):
    """Raised by network IO on socket EOF / timeout / reset. Lets the caller
    distinguish 'transport disconnected' from 'user typed quit' — these used
    to collapse into the same 'quit' sentinel and produced an exploitable
    edge case at the name prompt (a dropped client became a player called
    'quit')."""


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
                raise Disconnected("send during prompt failed")
        try:
            line = self._rfile.readline()
        except (socket.timeout, TimeoutError) as exc:
            raise Disconnected("idle timeout") from exc
        except (ConnectionResetError, OSError) as exc:
            raise Disconnected("connection reset") from exc
        if not line:
            raise Disconnected("EOF")
        return line.decode("utf-8", errors="replace").rstrip("\r\n").rstrip()


class WebIO(IO):
    """Queue-backed IO for browser sessions over SSE + POST.

    The Session loop runs in its own thread and uses this IO exactly as if
    it were a local terminal. Output `send()`s go onto `_send_q`, which is
    drained by the SSE writer thread and pushed to the browser as
    Server-Sent Event chunks. Input `receive()` blocks on `_recv_q`, which
    POST /input handlers push lines onto.

    Disconnection is one-way: when the browser closes or the session is
    GC'd by the idle reaper, `close()` is called. Any in-flight `receive()`
    wakes up within `_POLL_INTERVAL` seconds and raises Disconnected so the
    session loop can autosave and exit cleanly."""

    _POLL_INTERVAL = 1.0  # seconds; how often receive() rechecks the closed flag

    def __init__(self) -> None:
        self._send_q: queue.Queue[str] = queue.Queue()
        self._recv_q: queue.Queue[str] = queue.Queue()
        self._closed = threading.Event()

    def send(self, text: str) -> None:
        # Even after close, accept sends silently (the SSE drain may have
        # already torn down; we don't want a late epitaph crash to kill the
        # session's finalize path).
        if self._closed.is_set():
            return
        self._send_q.put(text)

    def receive(self, prompt: str = "> ") -> str:
        if prompt:
            self.send(prompt)
        while True:
            if self._closed.is_set():
                raise Disconnected("WebIO closed")
            try:
                line = self._recv_q.get(timeout=self._POLL_INTERVAL)
            except queue.Empty:
                continue
            # A None sentinel (pushed by close()) also signals disconnection.
            if line is None:
                raise Disconnected("WebIO closed")
            return line

    def push_input(self, line: str) -> None:
        """Called by the HTTP POST /input handler when the browser submits
        a line of input."""
        if self._closed.is_set():
            return
        self._recv_q.put(line)

    def drain_send(self, timeout: float) -> Optional[str]:
        """Called by the SSE writer to pull the next text chunk to push to
        the browser. Returns None on timeout (so the writer can send a
        keepalive comment) or when the IO has been closed."""
        try:
            return self._send_q.get(timeout=timeout)
        except queue.Empty:
            return None

    def close(self) -> None:
        """Signal the session that the connection is gone. Idempotent."""
        if self._closed.is_set():
            return
        self._closed.set()
        # Unblock any pending receive() immediately.
        try:
            self._recv_q.put_nowait(None)
        except queue.Full:
            pass

    @property
    def closed(self) -> bool:
        return self._closed.is_set()


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
