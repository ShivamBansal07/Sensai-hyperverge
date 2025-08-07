import uvicorn
import os

if __name__ == "__main__":
    # This ensures the app is run with the correct module path
    # and that the current working directory is the project root.
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8001, reload=True)
