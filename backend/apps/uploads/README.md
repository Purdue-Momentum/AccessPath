## File Upload Paths
### POST `/uploads/v1/files`
For single file uploads.
#### Examples
```
# Sample Uplaod
curl https://accesspath.purdue.edu/v1/files \
  -F "file"="@/path/to/a/file.jpg"
```
```
# Sample Response:
{
  "filename": "file.jpg",
  "file_id": "file_9f8b3c2d1e4a5f6",
  
}
```
### POST `/uploads/v1/files/batch`
For multiple file uploads.
(Urls generated via s3.presign_upload)
```
# Sample Response:
{
  "batch_id": "batch_xyz987",
  "uploads": [
    {
      "filename": "avatar.png",
      "file_id": "file_101",
      "upload_url": "<Presigned URL>",
      "method": "PUT"
    },
    {
      "filename": "resume.pdf",
      "file_id": "file_102",
      "upload_url": "<Presigned URL>",
      "method": "PUT" # So that the frontend knows what method to use; some cloud storage services use POST
    }
  ]
}
```
## PythonMagic for file validation