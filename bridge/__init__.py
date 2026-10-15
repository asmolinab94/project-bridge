"""Project Bridge: card reconciliation and September close. `build(data_dir)` is the single entry point."""

from collections import namedtuple

from bridge import checks, close, inputs, recon, treasury

Result = namedtuple("Result", ["inputs", "checks", "recon", "close", "treasury"])


def build(data_dir):
    """Chains the stages."""
    loaded = inputs.load(data_dir)
    reconciled = recon.reconcile(loaded)
    closed = close.build(loaded, reconciled)
    return Result(loaded, checks.run(loaded, reconciled, closed), reconciled, closed,
                  treasury.build(loaded, reconciled))
