from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class JSONSourceAdapter:
    source_type: str
    domain: str

    def normalize(self, payload: Any) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise ValueError("JSON payload must be an object")

        confidence = payload.get("confidence", 0.5)
        if isinstance(confidence, bool) or not isinstance(confidence, (int, float)):
            raise ValueError("confidence must be a number between 0 and 1")
        confidence = float(confidence)
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        location = payload.get("location")
        if location is not None and not isinstance(location, dict):
            raise ValueError("location must be an object")

        platform = payload.get("platform")
        if platform is not None and not isinstance(platform, str):
            raise ValueError("platform must be a string")

        content = payload.get("content", payload.get("raw_content"))
        if content is not None and not isinstance(content, str):
            raise ValueError("content must be a string")

        return {
            "source_type": self.source_type,
            "domain": self.domain,
            "platform": platform,
            "location": location,
            "raw_content": content,
            "confidence": confidence,
        }
