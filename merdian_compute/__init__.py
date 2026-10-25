"""merdian_compute — MERIDIAN's pure compute surface (S101, retail scope §1.3).

S101_MERDIAN_COMPUTE. Stdlib only. Importing this package reads no environment, opens no
client and touches no network (offline step 24 proves it). Retail pins this repo
by commit SHA; the contract is docs/interfaces/retail_compute_contract.md.
"""

from merdian_compute import cycle, gamma, volatility  # noqa: F401

__all__ = ["cycle", "gamma", "volatility"]
