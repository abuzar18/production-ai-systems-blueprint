from __future__ import annotations

import re
import uuid
from collections.abc import Iterable

from domain import Citation, SourceDocument, WorkflowResult, WorkflowStatus


TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9]+")
STOP_WORDS = {
    "a",
    "an",
    "and",
    "are",
    "for",
    "how",
    "in",
    "is",
    "of",
    "on",
    "should",
    "the",
    "this",
    "to",
    "we",
    "what",
    "with",
}


def _tokens(value: str) -> set[str]:
    return {
        token.lower()
        for token in TOKEN_PATTERN.findall(value)
        if token.lower() not in STOP_WORDS
    }


def _score(question: str, document: SourceDocument) -> float:
    query_tokens = _tokens(question)
    if not query_tokens:
        return 0.0
    document_tokens = _tokens(f"{document.title} {document.text}")
    overlap = len(query_tokens & document_tokens)
    return round(overlap / len(query_tokens), 3)


def retrieve(
    question: str,
    documents: Iterable[SourceDocument],
    limit: int = 3,
) -> list[tuple[SourceDocument, float]]:
    ranked = sorted(
        ((document, _score(question, document)) for document in documents),
        key=lambda item: (-item[1], item[0].source_id),
    )
    return [item for item in ranked if item[1] > 0][:limit]


def _first_sentence(text: str) -> str:
    sentence = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)[0]
    return sentence if sentence.endswith((".", "!", "?")) else f"{sentence}."


def _draft(question: str, evidence: list[tuple[SourceDocument, float]]) -> str:
    findings = " ".join(
        f"{_first_sentence(document.text)} [{document.source_id}]"
        for document, _ in evidence
    )
    return f"For ‘{question.strip()}’, the supplied evidence indicates: {findings}"


def _verify(answer: str, evidence: list[tuple[SourceDocument, float]]) -> bool:
    return bool(evidence) and all(
        f"[{document.source_id}]" in answer for document, _ in evidence
    )


def run_workflow(
    question: str,
    documents: Iterable[SourceDocument],
    request_id: str | None = None,
) -> WorkflowResult:
    clean_question = question.strip()
    if len(clean_question) < 5:
        raise ValueError("question must contain at least 5 characters")

    clean_documents = [
        document
        for document in documents
        if document.source_id.strip() and document.title.strip() and document.text.strip()
    ]
    if not clean_documents:
        raise ValueError("at least one non-empty document is required")

    workflow_id = request_id or str(uuid.uuid4())
    trace = ["planned"]
    evidence = retrieve(clean_question, clean_documents)
    trace.append("retrieved")

    if not evidence:
        trace.append("rejected")
        return WorkflowResult(
            request_id=workflow_id,
            status=WorkflowStatus.REJECTED,
            answer="The supplied documents do not contain enough relevant evidence to answer safely.",
            trace=trace,
        )

    answer = _draft(clean_question, evidence)
    trace.append("drafted")

    if not _verify(answer, evidence):
        trace.append("rejected")
        return WorkflowResult(
            request_id=workflow_id,
            status=WorkflowStatus.REJECTED,
            answer="The draft failed citation verification and was not published.",
            trace=trace,
        )

    trace.append("verified")
    citations = [
        Citation(
            source_id=document.source_id,
            title=document.title,
            score=score,
        )
        for document, score in evidence
    ]
    return WorkflowResult(
        request_id=workflow_id,
        status=WorkflowStatus.VERIFIED,
        answer=answer,
        citations=citations,
        trace=trace,
    )

