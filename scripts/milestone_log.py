#!/usr/bin/env python3
"""
Milestone logger for scale data pack generation.

Appends one line per batch milestone to /workspace/notes/gen-milestones.log

Format (machine-clean, no extra prose):
<ISO8601-UTC> | batch <id> | <N> calls | <N> new artifacts | <cumulative total> artifacts | spend: <N> requests, <credits> credits
"""

from datetime import datetime, timezone
from pathlib import Path


class MilestoneLogger:
    """Append-only milestone logger."""
    
    def __init__(self, milestones_file: str = "/workspace/notes/gen-milestones.log"):
        self.milestones_file = Path(milestones_file)
        self.milestones_file.parent.mkdir(parents=True, exist_ok=True)
        self.cumulative_artifacts = 0
        self.cumulative_calls = 0
        self.cumulative_credits = 0.0
    
    def log_batch(self, batch_id: str, calls: int, new_artifacts: int, credits: float | None = None):
        """
        Log a batch milestone.
        
        Args:
            batch_id: Batch identifier
            calls: Number of API calls in this batch
            new_artifacts: Number of new artifacts generated
            credits: Estimated credits spent (optional)
        """
        self.cumulative_calls += calls
        self.cumulative_artifacts += new_artifacts
        if credits is not None:
            self.cumulative_credits += credits
        
        ts = datetime.now(timezone.utc).isoformat()
        
        credits_str = f"{self.cumulative_credits:.2f}" if credits is not None else "N/A"
        
        line = f"{ts} | batch {batch_id} | {calls} calls | {new_artifacts} new artifacts | {self.cumulative_artifacts} artifacts | spend: {self.cumulative_calls} requests, {credits_str} credits\n"
        
        with open(self.milestones_file, "a") as f:
            f.write(line)
            f.flush()
        
        print(f"Milestone: {line.strip()}")
    
    def log_complete(self, total_artifacts: int, total_calls: int, total_tokens: int, credits: float | None = None):
        """Log completion."""
        ts = datetime.now(timezone.utc).isoformat()
        credits_str = f"{credits:.2f}" if credits is not None else "N/A"
        
        line = f"{ts} | COMPLETE | {total_calls} total calls | {total_artifacts} total artifacts | {total_tokens} total tokens | spend: {credits_str} credits\n"
        
        with open(self.milestones_file, "a") as f:
            f.write(line)
            f.flush()
        
        print(f"Complete: {line.strip()}")


if __name__ == "__main__":
    # Test
    logger = MilestoneLogger()
    logger.log_batch("test-001", 5, 5, 0.50)
    logger.log_batch("test-002", 10, 10, 1.00)
    logger.log_complete(15, 15, 5000, 1.50)
    print(f"\nCheck {logger.milestones_file}")
