from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SemanticIssue:
    fact: str
    narration_sentence: str
    similarity: float
    assessment: str


class SoftChecker:
    """Semantic contradiction detection using sentence embeddings."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info("Loading sentence-transformers model: %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
                logger.info("Model loaded successfully")
            except ImportError:
                logger.warning(
                    "sentence-transformers not installed, soft checking disabled"
                )
                self._model = "unavailable"

    def check(
        self,
        narration: str,
        established_facts: list[str],
        threshold: float = 0.75,
    ) -> list[SemanticIssue]:
        if not established_facts or not narration:
            return []

        self._load_model()
        if self._model == "unavailable" or self._model is None:
            return []

        sentences = [s.strip() for s in narration.split(".") if len(s.strip()) > 10]
        if not sentences:
            return []

        fact_texts = [f.replace("_", " ") for f in established_facts]

        try:
            all_texts = sentences + fact_texts
            embeddings = self._model.encode(all_texts, convert_to_tensor=True)

            sent_embs = embeddings[: len(sentences)]
            fact_embs = embeddings[len(sentences) :]

            from sentence_transformers.util import cos_sim
            sim_matrix = cos_sim(sent_embs, fact_embs)

            issues = []
            for i, sent in enumerate(sentences):
                for j, fact in enumerate(fact_texts):
                    score = sim_matrix[i][j].item()
                    if score >= threshold:
                        issues.append(
                            SemanticIssue(
                                fact=established_facts[j],
                                narration_sentence=sent,
                                similarity=score,
                                assessment=f"High similarity ({score:.2f}) between narration and fact - potential contradiction or redundancy",
                            )
                        )
            return issues

        except Exception as e:
            logger.error("Soft check failed: %s", e)
            return []

    def format_issues(self, issues: list[SemanticIssue]) -> str:
        if not issues:
            return ""
        lines = ["SEMANTIC CHECK FLAGS:"]
        for issue in issues:
            lines.append(
                f"  Narration: \"{issue.narration_sentence[:80]}...\"\n"
                f"  vs Fact: \"{issue.fact}\" (similarity: {issue.similarity:.2f})\n"
                f"  Assessment: {issue.assessment}"
            )
        return "\n".join(lines)
