#!/usr/bin/env python3
"""Start the application on loopback only."""

import uvicorn


if __name__ == "__main__":
    uvicorn.run("api.main:app", host="127.0.0.1", port=8000, reload=False)
