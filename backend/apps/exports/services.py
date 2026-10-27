"""
Lane E's public functions. Other apps call these and tasks.build_html_export, nothing else.

This file only reads review.Node and uploads.SourceFile. It never changes them.
"""

from collections import Counter

from django.db import transaction

from apps.review.models import Node
from apps.uploads.models import SourceFile

from .models import Export
from .rendering import ExportError

# EXPORTED is accepted too, so a lecture can be exported again later.
EXPORTABLE_STATES = {Node.State.APPROVED, Node.State.EXPORTED}
# Files that are still moving through the pipeline. Their nodes do not exist yet.
STILL_PROCESSING = {SourceFile.Status.UPLOADED, SourceFile.Status.PROCESSING}


def lecture_nodes(lecture) -> list[Node]:
    """Every node in the lecture, in reading order, with its current version loaded."""
    return list(
        Node.objects.filter(lecture=lecture)
        .select_related("current_version")
        .order_by("document__source_file__created_at", "order", "created_at")
    )


def export_blockers(lecture, nodes: list[Node] | None = None) -> list[str]:
    """Reasons this lecture can't be exported yet, in plain words. An empty list means it can."""
    nodes = lecture_nodes(lecture) if nodes is None else nodes
    blockers = []
    if lecture.source_files.filter(status__in=STILL_PROCESSING).exists():
        blockers.append("A file in this lecture is still being processed.")
    if not nodes:
        blockers.append("This lecture has no content yet.")
    waiting = Counter(n.get_state_display() for n in nodes if n.state not in EXPORTABLE_STATES)
    if waiting:
        total = sum(waiting.values())
        detail = ", ".join(f"{label}: {count}" for label, count in sorted(waiting.items()))
        blockers.append(f"{total} {'item is' if total == 1 else 'items are'} not approved yet ({detail}).")
    if any(n.current_version_id is None for n in nodes):
        blockers.append("Some items have no content yet.")
    return blockers


def class_label(klass) -> str:
    """The line above the lecture title, e.g. 'ME 27400 Dynamics, Fall 2026'."""
    label = f"{klass.course_code} {klass.name}".strip()
    return f"{label}, {klass.term}" if klass.term else label


def start_export(*, lecture, user) -> Export:
    """Create an Export and queue the build. Raises ExportError if the lecture isn't ready."""
    from .tasks import build_html_export  # imported here because tasks imports this module

    blockers = export_blockers(lecture)
    if blockers:
        raise ExportError(" ".join(blockers))
    export = Export.objects.create(klass_id=lecture.klass_id, lecture=lecture, created_by=user)
    # Queue only after the row is committed, so the worker can always find it.
    transaction.on_commit(lambda: build_html_export.delay(str(export.id)))
    return export