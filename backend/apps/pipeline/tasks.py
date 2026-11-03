"""Lane C tasks on the existing llm queue. Provider retries are bounded in client.py."""

from celery import shared_task

from .models import ProcessingRun, RevisionDraft
from .processing import prepare_revision, process


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def process_document(self, parsed_document_id: str) -> None:
    process(parsed_document_id)
    if ProcessingRun.objects.filter(document_id=parsed_document_id, status="running").exists():
        raise self.retry(countdown=60, max_retries=None)


@shared_task(bind=True, acks_late=True, reject_on_worker_lost=True)
def revise_node(self, revision_id: str) -> None:
    prepare_revision(revision_id)
    if RevisionDraft.objects.filter(pk=revision_id, status="running").exists():
        raise self.retry(countdown=60, max_retries=None)
