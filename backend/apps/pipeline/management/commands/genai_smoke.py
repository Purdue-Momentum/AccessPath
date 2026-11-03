"""Explicit, opt-in provider check using only synthetic text and a generated red square."""

import struct
import zlib

from django.core.management.base import BaseCommand, CommandError

from apps.classes.models import Class
from apps.pipeline import client, drafting
from apps.pipeline.contract import to_xml
from apps.pipeline.router import model_for


def red_square():
    def chunk(kind, data):
        return struct.pack('!I', len(data)) + kind + data + struct.pack('!I', zlib.crc32(kind + data) & 0xffffffff)
    header = struct.pack('!2I5B', 32, 32, 8, 2, 0, 0, 0)
    rows = (b'\0' + b'\xff\0\0' * 32) * 32
    return b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', header) + chunk(b'IDAT', zlib.compress(rows)) + chunk(b'IEND', b'')


class Command(BaseCommand):
    help = 'Run two synthetic Purdue requests, logging usage to the specified class. Requires --run-live.'

    def add_arguments(self, parser):
        parser.add_argument('--run-live', action='store_true')
        parser.add_argument('--class-id', required=True)

    def handle(self, *args, **options):
        if not options['run_live']:
            raise CommandError('Pass --run-live to explicitly enable network inference.')
        klass = Class.objects.get(pk=options['class_id'])
        key = f'classes/{klass.pk}/synthetic/red.png'
        manifest = drafting.asset_manifest([{'key': key, 'kind': 'image', 'page': 1}], klass.pk)
        try:
            document, models = drafting.draft_document(
                raw=b'<!-- Page: 1 -->\nA constant force of 3 newtons acts over 2 metres. The work is 6 joules.',
                manifest=manifest, context='Synthetic demonstration of work; the image is a simple colored square.',
                load_asset=lambda _: red_square(), accounting={'klass_id': klass.pk, 'source_file_id': None},
            )
            to_xml(document, context={'document': 'synthetic', 'lecture': 'synthetic',
                                      'source': 'synthetic', 'prompt_version': 'smoke'}, assets=manifest)
        except (client.ProviderError, ValueError) as exc:
            raise CommandError(f'Smoke check failed: {type(exc).__name__}') from None
        self.stdout.write(f'Validated {len(document["nodes"])} nodes and generated XML.')
        self.stdout.write(f'Text model: {model_for("text")}; vision model: {model_for("image")}')
        self.stdout.write(f'Reported models: {", ".join(sorted(set(models)))}')
        for node in document['nodes']:
            self.stdout.write(f'{node["kind"]}: {node["content"]}')
