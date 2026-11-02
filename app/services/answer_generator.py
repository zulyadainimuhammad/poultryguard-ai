
"""Generate source-grounded poultry answers using the Groq API."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from dotenv import load_dotenv
from groq import Groq

load_dotenv(override=True)


@dataclass(frozen=True)
class GeneratedAnswer:
    answer: str
    sources: tuple[dict[str, Any], ...]


class PoultryAnswerGenerator:
    """Generate answers from retrieved knowledge-base passages."""

    def __init__(self, model: str | None = None) -> None:
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError(
                "GROQ_API_KEY is missing. Add it to your local .env file."
            )

        self.model = model or os.getenv(
            "GROQ_MODEL", "openai/gpt-oss-120b"
        )
        self.client = Groq(api_key=api_key)

    def generate(
        self,
        question: str,
        passages: list[dict[str, Any]],
    ) -> GeneratedAnswer:
        """Answer a question using retrieved passages as evidence."""

        if not question or not question.strip():
            raise ValueError("Question cannot be empty.")

        if not passages:
            return GeneratedAnswer(
                answer=(
                    "I could not find relevant information in the "
                    "PoultryGuard knowledge base. Try rephrasing your "
                    "question or consult a qualified poultry professional."
                ),
                sources=(),
            )

        evidence_parts = []

        for index, passage in enumerate(passages, start=1):
            source = str(passage.get("source", "Unknown source"))
            section = str(passage.get("section", "Unspecified section"))
            content = str(passage.get("text", "")).strip()

            if content:
                evidence_parts.append(
                    f"[Source {index}]\n"
                    f"File: {source}\n"
                    f"Section: {section}\n"
                    f"Passage:\n{content}"
                )

        if not evidence_parts:
            return GeneratedAnswer(
                answer=(
                    "The retrieved passages did not contain usable text, "
                    "so I cannot provide a grounded answer."
                ),
                sources=(),
            )

        evidence = "\n\n".join(evidence_parts)

        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            max_tokens=900,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are PoultryGuard AI, an assistant for poultry "
                        "farming knowledge. Answer using only the supplied "
                        "evidence. Do not invent facts, treatments, drug "
                        "dosages, chemical concentrations, or procedures "
                        "not supported by the evidence. If the evidence "
                        "does not answer the question, say so clearly. "
                        "For suspected disease, severe illness, or flock "
                        "mortality, recommend contacting a qualified "
                        "veterinarian. Give practical, clear answers. "
                        "Cite supporting passages using their source file "
                        "paths, and distinguish general guidance from "
                        "information that needs professional confirmation."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Question:\n{question.strip()}\n\n"
                        f"Retrieved evidence:\n{evidence}\n\n"
                        "Provide a concise answer with supporting source "
                        "file paths. If the evidence is insufficient, "
                        "state that rather than guessing."
                    ),
                },
            ],
        )

        answer = response.choices[0].message.content

        if not answer or not answer.strip():
            raise RuntimeError("The AI provider returned an empty answer.")

        return GeneratedAnswer(
            answer=answer.strip(),
            sources=tuple(
                {
                    "source": passage.get("source", "Unknown source"),
                    "section": passage.get("section", "Unspecified section"),
                    "score": passage.get("score"),
                }
                for passage in passages
            ),
        )
