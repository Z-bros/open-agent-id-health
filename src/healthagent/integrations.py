"""Sponsor placeholders only. These are NOT functional integrations."""
class ZetarisEvidenceSource:
    def fetch(self, case_id: str, source: str):
        raise NotImplementedError("Confirm official Zetaris access and API docs first.")

class MeterlessEvaluator:
    def evaluate(self, review_package):
        raise NotImplementedError("Confirm official Meterless access and API docs first.")
