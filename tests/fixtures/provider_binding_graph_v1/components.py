"""Only synthetic credential/HTTP objects; no environment or network access."""
import json

from research_workbench.adapters.models.http import HttpResponse


class SyntheticCredential:
    label = "env:RWB_BINDING_SYNTHETIC_KEY"

    def __init__(self):
        self.resolutions = 0

    def available(self):
        raise AssertionError("source observation must not inspect environment presence")

    def resolve(self):
        self.resolutions += 1
        return "synthetic-binding-credential"


class SyntheticTransport:
    max_response_bytes = 65536

    def __init__(self):
        self.requests = []

    def send(self, request):
        self.requests.append(request)
        document = {"id": "graph-synthetic-response", "model": "deepseek-flash", "status": "completed",
                    "output": [{"type": "message", "role": "assistant", "content": [{"type": "output_text", "text": "7"}]}],
                    "usage": {"input_tokens": 5, "output_tokens": 2, "total_tokens": 7}}
        return HttpResponse(200, {}, json.dumps(document).encode())
