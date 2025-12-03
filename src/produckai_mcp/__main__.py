"""Main entry point for running as a module."""

import asyncio

from produckai_mcp.server import main

if __name__ == "__main__":
    asyncio.run(main())
