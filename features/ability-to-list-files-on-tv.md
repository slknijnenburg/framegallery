# Feature: Add the ability to list files on the Samsung Frame TV

In the frame_connector.py we have an interface to interact with the TV using the samsungtvws library. 
We will extend this interface to include a method for listing files on the TV.

## Acceptance criteria

* The frame_connector class gets a new list_files() method that can list the files on th TV. It should be possible to specify the image folder on the TV as argument, following the MY-C000X pattern.
* The list_files() method should return a list of dictionary objects, each containing the file name and any other file details that the websocket API provides.

## Implementation plan

### 1. Add list_files() method to FrameConnector class

**Location**: `framegallery/frame_connector/frame_connector.py`

**Method signature**:
```python
async def list_files(self, category: str = "MY-C0002") -> list[dict] | None:
    """
    List all files available on the Samsung Frame TV.

    Args:
        category: The image folder/category on the TV (default: "MY-C0002")
                 Common categories:
                 - "MY-C0002": User uploaded content (default)
                 - "MY-C0001": Samsung Art Store content
                 - "MY-C000X": Other categories following the pattern

    Returns:
        List of dictionaries containing file information from the TV,
        or None if the TV is not connected or an error occurs.
    """
```

### 2. Implementation details

The method will:
1. **Check connection status**: Verify TV is connected and online
2. **Call Samsung TV API**: Use `self._tv.available()` method to retrieve file list
3. **Filter by category**: If a specific category is provided, filter results
4. **Transform response**: Parse the TV's response into a standardized format
5. **Error handling**: Handle connection errors, timeouts, and invalid responses

**Expected return format**:
```python
[
    {
        "content_id": "MY-F0001",
        "category_id": "MY-C0002",
        "file_name": "image1.jpg",
        "file_type": "JPEG",
        "file_size": 1234567,
        "upload_date": "2024-01-15",
        "thumbnail_available": True,
        "matte": "none",
        # Additional metadata fields as provided by the TV
    },
    ...
]
```

### 3. Integration with existing error handling

- Utilize existing `TvNotConnectedError` and `TvConnectionTimeoutError` exceptions
- Follow the same connection check pattern as other methods (`_connected` and `_tv_is_online` flags)
- Use existing logger for debug/info/error messages

### 4. Testing approach

1. **Unit tests**: Mock the Samsung TV API responses
2. **Error scenarios**: Test disconnection, timeout, and invalid response handling

### 5. Future enhancements

- Add pagination support if the TV returns many files
- Implement thumbnail retrieval using `get_thumbnail()` API
- Add caching to avoid frequent API calls
- Support for filtering by file type or date range