from django.core.management.base import BaseCommand, CommandError

from apps.pipeline.tasks import process_document
from apps.uploads.models import ParsedDocument


class Command(BaseCommand):
    help = 'Queue an existing parsed document, or process inline with --inline. May call Purdue and S3.'

    def add_arguments(self, parser):
        parser.add_argument('document_id')
        parser.add_argument('--inline', action='store_true')

    def handle(self, *args, **options):
        try:
            document = ParsedDocument.objects.get(pk=options['document_id'])
        except (ParsedDocument.DoesNotExist, ValueError) as exc:
            raise CommandError('Parsed document not found') from exc
        if options['inline']:
            process_document(str(document.pk))
            self.stdout.write('Processing finished; inspect the processing run/job status.')
        else:
            task = process_document.delay(str(document.pk))
            self.stdout.write(f'Queued task {task.id}')
