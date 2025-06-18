import os
import shutil
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(
    tags=["admin"],
)

@router.get("/health")
async def health_check():
    return {"status": "ok"}

@router.post("/api/cleanup-cache")
async def cleanup_cache(request: Request):
    """
    Manually triggers the cleanup of the video cache.
    """
    video_cache = request.app.state.video_cache
    cleaned_count = 0
    errors = []
    
    cache_items = list(video_cache.items())

    for video_id, path in cache_items:
        try:
            dir_path = os.path.dirname(path)
            if os.path.isdir(dir_path):
                shutil.rmtree(dir_path)
                del video_cache[video_id]
                cleaned_count += 1
                print(f"   Manually removed cache directory: {dir_path}")
        except Exception as e:
            error_message = f"Error removing cache for {video_id}: {e}"
            print(error_message)
            errors.append(error_message)

    if errors:
        return JSONResponse(status_code=500, content={"message": f"Cleanup completed with {len(errors)} errors.", "errors": errors})
    
    if cleaned_count == 0:
        return JSONResponse(content={"message": "Video cache is already empty. No files to clean up."})

    return JSONResponse(content={"message": f"Successfully cleaned up {cleaned_count} cached video(s)."}) 