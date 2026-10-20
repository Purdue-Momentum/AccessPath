from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError;
from rest_framework import status
from backend.apps.storage.s3 import presign_upload

@api_view(['POST'])
def upload_file(request):
    filename = request.data.get('filename')
    mime_type = request.data.get('mime_type')
    
    if not filename or not mime_type:
        raise ValidationError({
            "detail": "Missing 'filename' or 'mime_type' fields."
        })
    
    upload_key =    