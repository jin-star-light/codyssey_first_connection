from app.errors import AIProviderError


class FakeAIClient:
    def __init__(self, answer="최근 학습시간이 증가했어요.", *, fail=False):
        self.answer = answer
        self.fail = fail
        self.system_prompt = None
        self.messages = None

    def complete(self, *, system_prompt, messages):
        self.system_prompt = system_prompt
        self.messages = messages
        if self.fail:
            raise AIProviderError("provider-secret-body")
        return self.answer
