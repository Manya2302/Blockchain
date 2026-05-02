"""
Management command: Process expired self-destructing documents.
Run periodically via cron or Celery beat:
  python manage.py process_expired
"""
from django.core.management.base import BaseCommand
from apps.evidence.expiry_engine import process_expired_documents


class Command(BaseCommand):
    help = 'Process and expire all self-destructing documents past their expiry time.'

    def handle(self, *args, **options):
        count = process_expired_documents()
        if count > 0:
            self.stdout.write(self.style.SUCCESS(f'Expired {count} document(s).'))
        else:
            self.stdout.write('No documents to expire.')
