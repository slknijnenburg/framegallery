## Frontend ability to view the files available on the television

## User Story

As a user, I want to be able to view the list of image files currently available on my Samsung Frame TV directly from the web interface, so that I can easily manage and select images for display.

## Acceptance criteria

- A new page is available in the React frontend called "Files on TV", which lists the files available on the TV.
- It lists the files with their name, the date of uploading and the file size.
- The page fetches the list of files from a new backend API endpoint that calls the `list_files()` method in the `FrameConnector` class.
- The page handles loading states and errors gracefully, displaying appropriate messages to the user.
- The page is accessible from the main navigation menu.

## Implementation plan

### Backend Implementation

#### 1. Create FrameConnector Dependency (framegallery/dependencies.py)
- Add `get_frame_connector()` function that returns the FrameConnector instance from `app.state.frame_connector`
- This allows dependency injection of the FrameConnector into API endpoints

#### 2. Create TV Files API Endpoint (framegallery/routers/tv_files.py)
- Create new router file for TV-related endpoints
- Implement `GET /api/tv/files` endpoint that:
  - Uses dependency injection to get FrameConnector instance
  - Calls `frame_connector.list_files()` method
  - Returns list of files with metadata (name, date, size, category)
  - Handles errors gracefully (TV offline, connection issues)
  - Accepts optional `category` query parameter (defaults to "MY-C0002" for user content)

#### 3. Create Response Schema (framegallery/schemas.py)
- Add `TvFileResponse` Pydantic model with fields:
  - `content_id: str` - Unique identifier from TV
  - `file_name: str` - Display name of the file
  - `file_type: str` - File format (JPEG, PNG, etc.)
  - `file_size: int | None` - File size in bytes
  - `date: str | None` - Upload/creation date
  - `category_id: str` - TV category identifier
  - `thumbnail_available: bool | None` - Whether thumbnail exists
  - `matte: str | None` - Applied matte style

#### 4. Register Router (framegallery/main.py)
- Import and include the new tv_files router in the FastAPI app
- Add to existing router includes

### Frontend Implementation

#### 5. Create TV Files Models (ui/src/models/TvFile.ts)
- TypeScript interface matching the backend response schema
- Export type for use in components

#### 6. Create TV Files Service (ui/src/services/tvFilesService.ts)
- API service function to fetch files from `/api/tv/files`
- Handle loading states and error conditions
- Support category filtering parameter

#### 7. Create TvFilesPage Component (ui/src/pages/TvFiles.tsx)
- Main page component that:
  - Fetches TV files data on mount
  - Displays loading spinner while fetching
  - Shows error message if TV is offline or request fails
  - Renders files in a table/grid format
  - Includes refresh button to reload data
  - Shows file details: name, date, size, format

#### 8. Create TvFileList Component (ui/src/components/TvFileList.tsx)
- Reusable component for displaying file list
- Use Material-UI Table or DataGrid for structured display
- Include columns for: File Name, Upload Date, File Size, Format
- Add sorting capabilities
- Show file count and category information

#### 9. Update App Navigation (ui/src/App.tsx)
- Add "Files on TV" navigation button to the AppBar
- Add new route `/tv-files` that renders TvFilesPage component
- Update routing configuration

#### 10. Add Loading and Error States
- Create loading skeleton/spinner for the files list
- Implement error boundary for graceful error handling
- Show appropriate messages for different error types:
  - TV offline/disconnected
  - Network connection issues
  - No files found

### Technical Considerations

#### Error Handling Strategy
- Backend returns appropriate HTTP status codes:
  - 200: Success with file list
  - 503: TV unavailable/offline
  - 500: Internal server error
- Frontend displays user-friendly error messages based on status codes

#### Performance Optimization
- Backend caches TV connection status to avoid repeated failed attempts
- Frontend implements debounced refresh to prevent excessive API calls
- Consider implementing polling for real-time updates if needed

#### User Experience Enhancements
- Add category filter dropdown (User Content, Art Store, etc.)
- Implement search/filter functionality for file names
- Show file thumbnails if available from TV
- Add file management actions (future enhancement)

### Implementation Steps

1. **Backend First Approach**:
   - Implement dependency injection for FrameConnector
   - Create API endpoint and test with existing list_files() method
   - Add response schemas and error handling

2. **Frontend Integration**:
   - Create TypeScript models and services
   - Build page components with loading/error states
   - Integrate with navigation and routing

3. **Testing & Refinement**:
   - Test with actual Samsung Frame TV connection
   - Verify error handling for offline scenarios
   - Ensure responsive design and accessibility

4. **Documentation**:
   - Update API documentation with new endpoint
   - Add user guide for the new feature

### Dependencies
- Requires existing FrameConnector.list_files() method (✅ already implemented)
- Uses existing FastAPI router pattern and Material-UI components
- Leverages current authentication and error handling patterns
