"""Tape T1-db: the Supabase sidecar for the tape (docs/tape/T1_db_plan.md). Offline loader, contracts, access.

Kept apart from services/tape_offline, whose every module is stdlib-only with no database or chain identifiers
(T1a guards proc-isolated / proc-no-outcomes). Not shipped by install.sh, not imported by services/tape_runner.
"""
