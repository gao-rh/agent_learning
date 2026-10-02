"""复用五个只读检索工具；全场景共享公开目录，不含私有答案或回复脚本。"""

import json
from pathlib import Path

from ..clarification_lab.knowledge import LabKnowledge

FIXTURES = Path(__file__).with_name("fixtures")


class ComplexKnowledge(LabKnowledge):
    def __init__(self, observations=()):
        self.catalog = json.loads((FIXTURES / "catalog.json").read_text())
        self.DIMENSIONS = self.catalog["dimensions"]
        self.metrics = {m["id"]: m for m in self.catalog["metrics"]}
        self.records = json.loads((FIXTURES / "knowledge.json").read_text())["records"]
        self.observations = list(observations)
