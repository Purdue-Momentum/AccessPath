"""Lane E. Celery tasks on the export queue."""

import logging

from celery import shared_task
from django.utils.text import slugify

from apps.storage import s3

from . import services
from .checks import check_html, errors_only
from .models import Export
from .rendering import ExportError, node_content, render_lecture

log = logging.getLogger(__name__)


@shared_task
def build_html_export(export_id: str) -> None:
    """
    Build the accessible HTML page for one lecture and save it to S3.

    Refuses unless every node in the lecture is approved. Builds real headings, MathML for
    equations and <figure> with alt text for images and graphs, with no node metadata.
    Records the exact NodeVersion ids used, so the export can be reproduced later.
    """
    export = Export.objects.select_related("klass", "lecture").get(id=export_id)
    if export.status != Export.Status.QUEUED:
        return  # already built or already failed. A retried message must not build it twice.

    try:
        nodes = services.lecture_nodes(export.lecture)
        blockers = services.export_blockers(export.lecture, nodes)
        if blockers:
            raise ExportError(" ".join(blockers))

        result = render_lecture(title=export.lecture.title, class_label=services.class_label(export.klass),
                                nodes=[node_content(n) for n in nodes], load_asset=s3.get_bytes)
        issues = check_html(result.html)
        export.check_report = ([{"level": "warning", "rule": "content", "message": w} for w in result.warnings]
                               + [issue.as_dict() for issue in issues])
        if errors_only(issues):
            raise ExportError("The page failed the accessibility check: "
                              + " ".join(issue.message for issue in errors_only(issues)))

        filename = f"{slugify(export.lecture.title) or 'lecture'}.html"
        key = s3.class_key(export.klass_id, "exports", export.id, filename)
        s3.put_bytes(key, result.html.encode("utf-8"), content_type="text/html; charset=utf-8")
    except ExportError as e:
        _fail(export, str(e))
        return
    except Exception:
        log.exception("Export %s crashed", export_id)
        _fail(export, "Something went wrong while building the page. Try again, and tell the team if it keeps "
                      "happening.")
        raise

    export.status = Export.Status.DONE
    export.html_s3_key = key
    export.version_ids = [str(n.current_version_id) for n in nodes]  # str, because JSON can't hold a UUID
    export.error = ""
    export.save(update_fields=["status", "html_s3_key", "version_ids", "error", "check_report", "updated_at"])


def _fail(export: Export, message: str) -> None:
    export.status = Export.Status.FAILED
    export.error = message
    export.save(update_fields=["status", "error", "check_report", "updated_at"])