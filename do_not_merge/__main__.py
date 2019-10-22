"""Main."""
import os
from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
import json
import traceback

routes = web.RouteTableDef()


@router.register("pull_request", action="labeled")
async def pull_labeled(event, gh, *args, **kwargs):
    print(json.dumps(event.data))


@router.register("pull_request", action="unlabeled")
async def pull_unlabeled(event, gh, *args, **kwargs):
    print(json.dumps(event.data))


@routes.post("/")
async def main(request):

    try:
        # Get payload
        payload = await request.read()

        # Get authtentication
        secret = os.environ.get("GH_SECRET")
        token = os.environ.get("GH_AUTH")
        event = sansio.Event.from_http(request.headers, payload, secret=secret)

        # Handle ping
        if event.event == "ping":
            return web.Response(status=200)

        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, "isaac-muse/do-not-merge", oauth_token=token)

            await asyncio.sleep(1)
            await router.dispatch(event, gh)

        return web.Response(status=200)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    port = os.environ.get("PORT")
    if port is not None:
        port = int(port)

    web.run_app(app, port=port)
