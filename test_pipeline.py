import unittest

from domain import SourceDocument, WorkflowStatus
from pipeline import retrieve, run_workflow


class PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.documents = [
            SourceDocument(
                source_id="runbook",
                title="Reliability Runbook",
                text=(
                    "Reliable services use health checks, request IDs, structured logs, "
                    "automated tests, and rollback-ready deployments."
                ),
            ),
            SourceDocument(
                source_id="security",
                title="Security Standard",
                text="Services validate input, use least privilege, and never log secrets.",
            ),
        ]

    def test_retrieval_ranks_relevant_document_first(self) -> None:
        evidence = retrieve("Which health checks make services reliable?", self.documents)
        self.assertEqual(evidence[0][0].source_id, "runbook")
        self.assertGreater(evidence[0][1], 0)

    def test_verified_workflow_includes_trace_and_citations(self) -> None:
        result = run_workflow(
            "How do health checks improve reliability?",
            self.documents,
            request_id="test-request",
        )
        self.assertEqual(result.status, WorkflowStatus.VERIFIED)
        self.assertEqual(result.request_id, "test-request")
        self.assertIn("verified", result.trace)
        self.assertIn("[runbook]", result.answer)
        self.assertTrue(result.citations)

    def test_irrelevant_evidence_is_rejected(self) -> None:
        result = run_workflow("Explain lunar geology", self.documents)
        self.assertEqual(result.status, WorkflowStatus.REJECTED)
        self.assertEqual(result.citations, [])
        self.assertEqual(result.trace, ["planned", "retrieved", "rejected"])

    def test_invalid_question_fails_fast(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 5 characters"):
            run_workflow("AI", self.documents)


if __name__ == "__main__":
    unittest.main()

