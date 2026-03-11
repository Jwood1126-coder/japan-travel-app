"""Shared test configuration.

Backs up and restores japan_trip.db so mutation tests in test_services.py
don't affect test_smoke.py on subsequent runs.
"""
import os
import shutil

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'japan_trip.db')
SEED_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'seed.db')


def pytest_sessionfinish(session, exitstatus):
    """Restore japan_trip.db from seed after all tests complete."""
    if os.path.exists(SEED_PATH):
        shutil.copy2(SEED_PATH, DB_PATH)
