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
