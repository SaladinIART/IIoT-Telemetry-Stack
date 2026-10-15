from __future__ import annotations

import logging

LOG = logging.getLogger("alerting.anomaly")


class AnomalyScorer:
    """
    Per-(asset, signal) IsolationForest anomaly scorer.

    Cold-start guard: no scoring until min_samples have been collected.
    Refits the model every refit_every additional samples so the baseline
    tracks seasonal/operational drift without growing unboundedly.

    sklearn is imported lazily to avoid adding startup latency when the
    service is used in environments where the model is not yet ready.
    """

    def __init__(
        self,
        min_samples: int = 50,
        refit_every: int = 500,
        threshold: float = -0.1,
    ) -> None:
        self.min_samples = min_samples
        self.refit_every = refit_every
        self.threshold = threshold
        self._samples: list[float] = []
        self._total_seen: int = 0
        self._model = None  # IsolationForest, set after first refit

    @property
    def ready(self) -> bool:
        return self._model is not None

    def add(self, value: float) -> None:
        """Record a new sample. Triggers a model refit at configured milestones."""
        self._samples.append(value)
        self._total_seen += 1
        # Keep rolling buffer bounded to avoid unbounded memory growth
        if len(self._samples) > self.refit_every * 2:
            self._samples = self._samples[-self.refit_every :]
        # Refit on first milestone and every refit_every samples thereafter
        if self._total_seen == self.min_samples or (
            self._total_seen > self.min_samples and self._total_seen % self.refit_every == 0
        ):
            self._refit()

    def _refit(self) -> None:
        try:
            from sklearn.ensemble import IsolationForest  # lazy import

            model = IsolationForest(contamination=0.05, random_state=42, n_jobs=1)
            model.fit([[v] for v in self._samples])
            self._model = model
            LOG.debug(
                "model refit",
                extra={"event": {"samples": len(self._samples), "total_seen": self._total_seen}},
            )
        except Exception as exc:
            LOG.warning("model refit failed", extra={"event": {"error": str(exc)}})

    def score(self, value: float) -> float:
        """
        Return the IsolationForest anomaly score for this value.
        Lower = more anomalous. Returns 0.0 if the model is not yet ready.
        """
        if not self.ready or self._model is None:
            return 0.0
        return float(self._model.score_samples([[value]])[0])

    def is_anomaly(self, value: float) -> bool:
        """Return True if value is below the configured anomaly score threshold."""
        return self.ready and self.score(value) < self.threshold
