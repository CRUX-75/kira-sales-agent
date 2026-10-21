"""Test doubles. No test in this repository depends on a real LLM provider."""

from app.application.wording import WordingRequest


class ScriptedClient:
    """Returns scripted outputs in order; an Exception instance in the script is raised."""

    def __init__(self, *outputs):
        self.outputs = list(outputs)
        self.requests: list[WordingRequest] = []

    def reword(self, request: WordingRequest) -> str:
        self.requests.append(request)
        output = self.outputs.pop(0)
        if isinstance(output, Exception):
            raise output
        return output


class EchoClient:
    """Always returns the base text: valid by construction. Reports fixed token usage."""

    def __init__(self):
        self.last_usage = None

    def reword(self, request):
        from app.application.wording import Usage

        self.last_usage = Usage(100, 20)
        return request.base_text


class BrokenClient:
    """Always returns an invalid text (exclamation mark)."""

    def reword(self, request):
        return "Das geht leider nicht!"


class FailingClient:
    def reword(self, request):
        raise TimeoutError("provider timeout")
