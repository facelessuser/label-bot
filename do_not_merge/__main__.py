"""Main."""
import asyncio
import aiohttp
import os
import sys
import json
import cachetools
import urllib.parse
import traceback
import yaml
from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from . import wip_label
from . import wildcard_labels
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

router = routing.Router()
routes = web.RouteTableDef()
cache = cachetools.LRUCache(maxsize=500)


async def get_config(event, gh):
    """Get label configuration file."""

    try:
        content = await gh.getitem(
            event.data['pull_request']['head']['repo']['content_url'].replace('{+path}', file),
            {'ref': sha},
            sansio.accept_format(version="v3", media='raw', json=False)
        )
        config = yaml.load(content, Loader=Loader)
    except Exception:
        config = {'wip': ['wip', 'work in progress', 'work-in-progress']}

    print(json.dumps(config))
    return config


@router.register("pull_request", action="labeled")
async def pull_labeled(event, gh, *args, **kwargs):
    """Handle pull request labeled event."""

    config = await get_config(event, gh)
    await wip_label.wip(event, gh, config)


@router.register("pull_request", action="unlabeled")
async def pull_unlabeled(event, gh, *args, **kwargs):
    """Handle pull request unlabeled event."""

    config = await get_config(event, gh)
    await wip_label.wip(event, gh, config)


@router.register("pull_request", action="reopened")
async def pull_reopened(event, gh, *args, **kwargs):
    """Handle reopened events."""

    config = await get_config(event, gh)
    await wildcard_labels.wildcard_labels(event, gh, config)
    await wip_label.wip(event, gh, config)


@router.register("pull_request", action="opened")
async def pull_opened(event, gh, *args, **kwargs):
    """Handle opened events."""

    config = get_config(event, gh)
    await wildcard_labels.wildcard_labels(event, gh, config)


@router.register("pull_request", action="synchronize")
async def pull_synchronize(event, gh, *args, **kwargs):
    """Handle synchronization events."""

    config = get_config(event, gh)
    await wildcard_labels.wildcard_labels(event, gh, config)


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
            gh = gh_aiohttp.GitHubAPI(session, "gir-bot", oauth_token=token, cache=cache)

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
