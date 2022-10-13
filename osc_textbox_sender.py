from collections import deque
import time

from pythonosc.udp_client import SimpleUDPClient


def splitToMax(text: str, limit: int) -> list[str]:
    strings: list[list[str]] = []
    currString: list[str] = []

    for word in text.split(" "):
        if len(" ".join(currString + [word])) <= limit:
            currString.append(word)
        else:
            strings.append(currString)
            currString = [word]

    # Turn the strings array of array into an array of strings and add the currstring
    # to the tail of it so we don't miss the last sentence we parsed.
    return [" ".join(string) for string in strings] + [" ".join(currString)]


class OSCTextboxSender:
    def __init__(self, ip: str, port: int, refresh_rate: float = 5) -> None:
        self._ip = ip
        self._port = port
        self._client = SimpleUDPClient(self._ip, self._port)
        self._refresh_rate = refresh_rate

        self._queue: deque[str] = deque()
        self._last_displayed = time.time() - self._refresh_rate
        self._user_typing = False
    
    def _update_typing(self, typing: bool) -> None:
        self._client.send_message("/chatbox/typing", typing)

    @property
    def typing(self) -> bool:
        return self._user_typing
    
    @typing.setter
    def typing(self, new_value: bool) -> None:
        if self._user_typing != new_value:
            self._update_typing(new_value)
        self._user_typing = new_value

    def set_ip_port(self, ip: str, port: int) -> None:
        if ip != ip or port != port:
            self._ip = ip
            self._port = port
            self._client = SimpleUDPClient(self._ip, self._port)

    def display(self, string: str) -> None:
        # Split the string into enough bits so that it can be safely but on the queue
        self._queue.extend(splitToMax(string, 144))

    def update(self) -> None:
        can_update = self._last_displayed < time.time() - self._refresh_rate
        if len(self._queue) > 0 and can_update:
            self._client.send_message("/chatbox/input", (self._queue.popleft(), True))
            self._last_displayed = time.time()
