from typing import List, Dict, Any, Optional

class Chat:
    def __init__(
        self,
        history: List[Dict[str, Any]],
        duration: float,
        nr_tokens: int,
        interactions: int,
        nr_generated_scripts: str,
        nr_code_errors: str,
        summary: str,
        gherkin: bool
    ):
        self.history = history
        self.duration = duration
        self.interactions = interactions
        self.nr_generated_scripts = nr_generated_scripts
        self.nr_code_errors = nr_code_errors
        self.nr_tokens = nr_tokens
        self.summary = summary
        self.gherkin = gherkin

    def to_dict(self) -> Dict[str, Any]:
        return {
            "history": self.history,
            "duration": self.duration,
            "summary": self.summary,
            "nr_tokens": self.nr_tokens,
            "gherkin": self.gherkin,
        }