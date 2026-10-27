import asyncio

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..events import bus, sse_format

router = APIRouter()


@router.get("/recent")
def recent():
    return bus.snapshot()[-50:]


@router.get("/stream")
async def stream(request: Request, token: str | None = Query(default=None)):
    if not token:
        raise HTTPException(status_code=401, detail="Token required")
    from ..security import decode_token
    try:
        decode_token(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")
    q = bus.subscribe()

    async def gen():
        try:
            for event in bus.snapshot()[-20:]:
                yield sse_format(event)
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=20)
                    yield sse_format(event)
                except asyncio.TimeoutError:
                    yield ": heartbeat\n\n"
        finally:
            bus.unsubscribe(q)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
