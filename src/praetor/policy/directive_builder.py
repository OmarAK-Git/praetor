"""Build ContainmentDirective records from PolicyGate authorization."""

from praetor.containment.lifecycle import build_proposed_directive_in_transaction

# Backward-compatible alias for Task 17 import paths.
build_containment_directive_in_transaction = build_proposed_directive_in_transaction

__all__ = [
    "build_containment_directive_in_transaction",
    "build_proposed_directive_in_transaction",
]
