## File Upload Paths
### POST `/uploads/classes/<uuid:class_id>/files/`
#### Examples
```
# Sample Request:
```
```
# Sample Response:
{
  "results": [
    {
      "id": "6239c7cd-dd1f-450e-a70b-443064933cd7",
      "filename": "lecture_slides.pdf",
      "s3_key": "classes/8ac8b8b4-2349-47d0-aade-57715b2b7242/uploads/f88a75b6-2fbd-4bd7-9902-06fb8b4a853f/lecture_slides.pdf"
    },
    {
      "id": "ff3457f3-39e9-4504-b7ff-47cc1b39cd1b",
      "filename": "diagram.png",
      "s3_key": "classes/c4c0361a-2076-4e32-ad7d-db93ceb59b21/uploads/44fdafdc-bb1d-4f08-a392-a583a5cc3ed7/diagram.png"
    }
  ]
}
```
## TODO
- Figure out what authentication looks like
- Complete sample upload
- Ensure that the lecture belongs to the class
## Notes
- Name is passed in to urlpatterns to ensure that reverse can be used in unit test independently of path