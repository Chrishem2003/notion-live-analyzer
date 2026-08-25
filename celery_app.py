"""
celery_app.py — Async task runner for CHRISHEM Unified Platform.

Why this exists: several hub pages (Literature & Publishing Hub's bulk paper
harvesting, Data Studio's large-file profiling, Domain Analytics Hub's
audits) currently do their heavy lifting inline, inside the Streamlit
request. That blocks the UI thread for every user on that server, not just
the one who kicked off the job, and it dies if the browser tab is closed
mid-run. This module moves that work onto Celery workers backed by Redis,
so Streamlit only ever submits a job and polls a job id.

Configuration is entirely via environment variables — nothing here assumes
a specific deployment. Defaults point at a local Redis for development.
"""

import os
from celery import Celery
from kombu import Queue

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

# Separate DB index for results so a broker flush doesn't wipe job history,
# and so you can point results at a different Redis instance in prod if you
# want the broker and the result store to scale independently.
RESULT_BACKEND_URL = os.environ.get("CELERY_RESULT_BACKEND", REDIS_URL)

celery_app = Celery(
    "chrishem_platform",
    broker=REDIS_URL,
    backend=RESULT_BACKEND_URL,
    include=["tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Progress reporting relies on result persistence — don't let it disappear
    # before a slow user comes back to check on a 50-paper harvest.
    result_expires=60 * 60 * 24,  # 24h

    # A worker that dies mid-task (OOM, deploy restart) shouldn't silently
    # lose the job — re-queue it rather than mark it "lost".
    task_acks_late=True,
    worker_prefetch_multiplier=1,

    # Hard ceilings so a runaway job (e.g. a literature query that somehow
    # matches millions of records) can't starve the whole worker pool.
    task_soft_time_limit=60 * 15,   # 15 min: raises SoftTimeLimitExceeded, task can clean up
    task_time_limit=60 * 20,        # 20 min: hard kill

    # Route by sector so a slow bioinformatics audit doesn't queue behind
    # a burst of quick literature searches, or vice versa.
    task_queues=(
        Queue("literature"),
        Queue("data_audit"),
        Queue("agents"),
        Queue("default"),
    ),
    task_routes={
        "tasks.harvest_literature_task": {"queue": "literature"},
        "tasks.bulk_dataset_audit_task": {"queue": "data_audit"},
        # Agent swarm runs mix a network call (CrossRef) with an optional LLM
        # call — kept off the literature queue so a burst of quick searches
        # can't starve a slower swarm run, or vice versa.
        "tasks.run_swarm_task": {"queue": "agents"},
    },
    task_default_queue="default",
)

if __name__ == "__main__":
    celery_app.start()