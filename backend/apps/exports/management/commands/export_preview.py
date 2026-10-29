"""
Writes a lecture's export to a local HTML file, without S3 upload or Celery.
For checking the page by eye, with axe and with a screen reader.

    python manage.py export_preview <lecture_id> --out preview.html
    python manage.py export_preview <lecture_id> --draft     # include nodes that are not approved yet

Nothing is saved to the database or S3. Never send a --draft file to students.
"""

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from apps.classes.models import Lecture
from apps.exports import services
from apps.exports.checks import check_html
from apps.exports.rendering import ExportError, node_content, render_lecture
from apps.storage import s3


def _try_load(key: str) -> bytes | None:
    try:
        return s3.get_bytes(key)
    except Exception:
        return None  # no MinIO running, or the asset is missing. The figure falls back to its description.


class Command(BaseCommand):
    help = "Render one lecture's accessible HTML to a local file."

    def add_arguments(self, parser):
        parser.add_argument("lecture_id")
        parser.add_argument("--out", default="export-preview.html")
        parser.add_argument("--draft", action="store_true", help="Render even if some nodes are not approved.")

    def handle(self, *args, lecture_id, out, draft, **options):
        lecture = Lecture.objects.select_related("klass").filter(id=lecture_id).first()
        if lecture is None:
            raise CommandError(f"No lecture with id {lecture_id}.")
        nodes = services.lecture_nodes(lecture)
        blockers = services.export_blockers(lecture, nodes)
        if blockers and not draft:
            raise CommandError("Not ready to export. " + " ".join(blockers) + " Add --draft to preview anyway.")
        try:
            result = render_lecture(title=lecture.title, class_label=services.class_label(lecture.klass),
                                    nodes=[node_content(n) for n in nodes if n.current_version_id],
                                    load_asset=_try_load)
        except ExportError as e:
            raise CommandError(str(e)) from e

        Path(out).write_text(result.html, encoding="utf-8")
        for warning in result.warnings:
            self.stdout.write(self.style.WARNING(f"warning  {warning}"))
        for issue in check_html(result.html):
            style = self.style.ERROR if issue.level == "error" else self.style.WARNING
            self.stdout.write(style(f"{issue.level:<8} {issue.rule}: {issue.message}"))
        self.stdout.write(self.style.SUCCESS(f"Wrote {out}. Open it in a browser, then test with VoiceOver or NVDA."))