"""fail-closed credit and request governor for the task-10 provider batch."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


class BudgetExceeded(RuntimeError):
    """raised before a call that would cross a configured batch boundary."""


@dataclass(frozen=True)
class Reservation:
    """one pre-call reservation against the shared batch budget."""

    call_number: int
    credits: Decimal


class CreditBudget:
    """sequential batch governor using the published glm-53-flash rates."""

    INPUT_CREDITS_PER_MILLION = Decimal("0.15")
    OUTPUT_CREDITS_PER_MILLION = Decimal("0.50")
    MAX_PROMPT_BYTES = 8192
    WRAPPER_TOKEN_ALLOWANCE = 4096
    # or6 evidence (2026-11-08 probe): glm-53-flash spent the entire 256-token
    # budget on reasoning before any visible text (reasoning_tokens == 256,
    # status "incomplete"). 1024 leaves room for reasoning + a bounded answer;
    # full-matrix cost stays trivial: 512 calls x 1024 x 0.50/M ~= 0.26 credits.
    MAX_OUTPUT_TOKENS = 1024

    def __init__(self, ceiling_credits: str, max_calls: int):
        ceiling = Decimal(ceiling_credits)
        if ceiling <= 0 or max_calls <= 0:
            raise ValueError("credit ceiling and call limit must be positive")
        self.ceiling = ceiling
        self.max_calls = max_calls
        self.calls_started = 0
        self.calls_completed = 0
        self.calls_failed = 0
        self.credits_accounted = Decimal(0)

    @classmethod
    def max_call_reservation(cls) -> Decimal:
        """return the conservative reservation for one bounded request."""
        input_tokens = cls.MAX_PROMPT_BYTES + cls.WRAPPER_TOKEN_ALLOWANCE
        return (
            Decimal(input_tokens) * cls.INPUT_CREDITS_PER_MILLION
            + Decimal(cls.MAX_OUTPUT_TOKENS) * cls.OUTPUT_CREDITS_PER_MILLION
        ) / Decimal(1_000_000)

    def preflight(self, planned_calls: int) -> dict[str, str | int]:
        """prove the declared matrix fits both request and credit limits."""
        if planned_calls < 0 or planned_calls > self.max_calls:
            raise BudgetExceeded("planned call count exceeds batch call limit")
        maximum = self.max_call_reservation() * planned_calls
        if maximum > self.ceiling:
            raise BudgetExceeded("planned matrix exceeds credit ceiling")
        return {
            "planned_calls": planned_calls,
            "call_limit": self.max_calls,
            "credit_ceiling": format(self.ceiling, "f"),
            "max_reserved_credits": format(maximum, "f"),
            "max_output_tokens_per_call": self.MAX_OUTPUT_TOKENS,
        }

    def begin(self, prompt: str) -> Reservation:
        """reserve one request before provider transport is invoked."""
        if len(prompt.encode("utf-8")) > self.MAX_PROMPT_BYTES:
            raise BudgetExceeded("prompt exceeds the bounded provider envelope")
        if self.calls_started >= self.max_calls:
            raise BudgetExceeded("batch call limit reached")
        reserved = self.max_call_reservation()
        if self.credits_accounted + reserved > self.ceiling:
            raise BudgetExceeded("batch credit ceiling reached")
        self.calls_started += 1
        return Reservation(self.calls_started, reserved)

    @classmethod
    def _token_cost(cls, input_tokens: int, output_tokens: int) -> Decimal:
        if input_tokens < 0 or output_tokens < 0:
            raise ValueError("token counts must be non-negative")
        return (
            Decimal(input_tokens) * cls.INPUT_CREDITS_PER_MILLION
            + Decimal(output_tokens) * cls.OUTPUT_CREDITS_PER_MILLION
        ) / Decimal(1_000_000)

    @staticmethod
    def _provider_credit(value: Any) -> Decimal | None:
        if value is None:
            return None
        try:
            parsed = Decimal(str(value))
        except (InvalidOperation, ValueError):
            return None
        return parsed if parsed >= 0 else None

    def finish(
        self,
        reservation: Reservation,
        *,
        input_tokens: int,
        output_tokens: int,
        provider_credits: Any = None,
    ) -> Decimal:
        """account a completed call conservatively and return its charge."""
        if output_tokens > self.MAX_OUTPUT_TOKENS:
            raise BudgetExceeded("provider exceeded the bounded output envelope")
        token_cost = self._token_cost(input_tokens, output_tokens)
        provider_cost = self._provider_credit(provider_credits)
        accounted = max(token_cost, provider_cost or Decimal(0))
        if accounted > reservation.credits:
            raise BudgetExceeded("provider charge exceeded the pre-call reservation")
        self.credits_accounted += accounted
        self.calls_completed += 1
        return accounted

    def fail(self, reservation: Reservation) -> None:
        """retain the full reservation when no trustworthy receipt is returned."""
        self.credits_accounted += reservation.credits
        self.calls_failed += 1

    def summary(self) -> dict[str, str | int]:
        return {
            "call_limit": self.max_calls,
            "calls_started": self.calls_started,
            "calls_completed": self.calls_completed,
            "calls_failed": self.calls_failed,
            "credit_ceiling": format(self.ceiling, "f"),
            "credits_accounted": format(self.credits_accounted, "f"),
        }
