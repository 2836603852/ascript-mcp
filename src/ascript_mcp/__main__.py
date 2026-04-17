"""允许 python -m ascript_mcp 直接启动本地 stdio 服务。"""

import asyncio
from ascript_mcp.local import main

asyncio.run(main())
