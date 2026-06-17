from fastapi import APIRouter, Request, Query
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import Response, HTMLResponse
import urllib.parse
import time

from app.services import clock, weather as weather_svc, jewish_cal as jewish_cal_svc

router = APIRouter()

DEFAULT_FONT = clock.DEFAULT_FONT


@router.get(
    "/",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
@router.get(
    "/clock",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
@router.get(
    "/clock.png",
    responses={200: {"content": {"image/png": {}}}},
    response_class=Response,
)
async def get_clock(
    request:  Request,
    font:      str = Query(default=DEFAULT_FONT),
    sleeptime: str = Query(default="0"),
    location:  str = Query(default="Tel Aviv"),
    calendar:  str = Query(default="gregorian"),
) -> Response:
    loc = location or "Tel Aviv"
    w = await weather_svc.get_weather(loc, request.app.state.http_client)

    jdate = None
    if calendar == "jewish":
        today = clock.get_israel_time().date()
        jdate = await jewish_cal_svc.get_jewish_date(today, request.app.state.http_client)

    img_bytes = await run_in_threadpool(
        clock.generate_clock_image,
        font_name   = font,
        sleep_time  = sleeptime == "1",
        weather     = w,
        jewish_date = jdate,
    )
    return Response(
        content=img_bytes,
        media_type="image/png",
        headers={"Cache-Control": "no-cache"},
    )

@router.get(
    "/kindle",
    response_class=HTMLResponse,
)
async def get_kindle(
    request:  Request,
    font:      str = Query(default=DEFAULT_FONT),
    sleeptime: str = Query(default="0"),
    location:  str = Query(default="Tel Aviv"),
    calendar:  str = Query(default="gregorian"),
) -> HTMLResponse:
    params = urllib.parse.urlencode({
        "font": font,
        "sleeptime": sleeptime,
        "location": location,
        "calendar": calendar,
        "_t": int(time.time())
    })
    img_url = f"/clock.png?{params}"
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="refresh" content="60">
    <title>Hebrew Clock - Kindle</title>
    <style>
        body, html {{
            margin: 0;
            padding: 0;
            width: 100%;
            height: 100%;
            overflow: hidden;
            background-color: white;
        }}
        .rotated-container {{
            position: absolute;
            top: 50%;
            left: 50%;
            width: 100vh;
            height: 100vw;
            transform: translate(-50%, -50%) rotate(90deg);
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        img {{
            width: 100%;
            height: 100%;
            object-fit: fill;
            image-rendering: pixelated;
        }}
    </style>
</head>
<body>
    <div class="rotated-container">
        <img id="clock-img" src="{img_url}" alt="Clock">
    </div>
</body>
</html>"""
    return HTMLResponse(
        content=html,
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
            "Expires": "0",
        }
    )
