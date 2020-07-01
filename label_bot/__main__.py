"""Main."""
import asyncio
import aiohttp
import os
import sys
import cachetools
import traceback
from aiohttp import web
from aiojobs.aiohttp import setup, spawn, get_scheduler_from_app
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from . import wip_labels
from . import sync_labels
from . import triage_labels
from . import commands
from . import util
__version__ = '1.9.0'

router = routing.Router()
routes = web.RouteTableDef()
cache = cachetools.LRUCache(maxsize=500)

sem = asyncio.Semaphore(1)


async def deferred_commands(event):
    """Defer handling of commands in comments."""

    async with sem:
        async with aiohttp.ClientSession() as session:
            token = os.environ.get("GH_AUTH")
            bot = os.environ.get("GH_BOT")
            gh = gh_aiohttp.GitHubAPI(session, bot, oauth_token=token, cache=cache)
            await asyncio.sleep(1)
            async for cmd in commands.run(event, gh, bot):
                if cmd.pending is not None:
                    await cmd.pending(cmd.event, gh)

                await get_scheduler_from_app(app).spawn(
                    deferred_task(cmd.command, cmd.event, kwargs=cmd.kwargs)
                )


async def deferred_task(function, event, kwargs=None):
    """Defer the event work."""

    if kwargs is None:
        kwargs = {}

    async with sem:
        async with aiohttp.ClientSession() as session:
            token = os.environ.get("GH_AUTH")
            bot = os.environ.get("GH_BOT")
            gh = gh_aiohttp.GitHubAPI(session, bot, oauth_token=token, cache=cache)

            # If we need to make sure the task is working with live issue labels, turn off quick labels.
            await asyncio.sleep(1)
            config = await event.get_config(gh)
            await function(event, gh, config, **kwargs)


@router.register("pull_request", action="labeled")
@router.register("pull_request", action="unlabeled")
async def pull_label_events(event, gh, request, *args, **kwargs):
    """
    Handle pull label events.

    These types of events just require us to handle: WIP.
    """

    event = util.Event(event.event, event.data)
    if event.state != "open":
        return

    await spawn(request, deferred_task(wip_labels.run, event))


@router.register("pull_request", action="synchronize")
@router.register("pull_request", action="reopened")
@router.register("pull_request", action="opened")
async def pull_sync_events(event, gh, request, *args, **kwargs):
    """
    Handle any event that requires us to be aware of file changes.

    These types of events we want to handle: WIP, review, and adjusting labels by file changes.
    """

    event = util.Event(event.event, event.data)
    if event.state != "open":
        return

    await spawn(request, deferred_task(commands.run_all_pull_actions, event))


@router.register("issues", action="opened")
async def issues_open_events(event, gh, request, *args, **kwargs):
    """
    Handle issues open events.

    Apply a triage label (if needed) to new issues.
    """

    event = util.Event(event.event, event.data)
    await spawn(request, deferred_task(triage_labels.run, event))


@router.register('push', ref='refs/heads/master')
async def push(event, gh, request, *args, **kwargs):
    """
    Handle push events on master.

    When pushing to master, we want to resync the labels with the latest config file.
    """

    event = util.Event(event.event, event.data)
    await asyncio.sleep(1)
    await sync_labels.pending(event, gh)
    await spawn(request, deferred_task(sync_labels.run, event))


@router.register("issues", action="opened")
@router.register("pull_request", action="opened")
@router.register('issue_comment', action="created")
async def issue_comment_created(event, gh, request, *args, **kwargs):
    """
    Handle issue comment created.

    On any issue/pull request creation, check the body for sync requests,
    and in any comments, check for command requests that are appropriate
    for the issue type.
    """

    # Only allow collaborators or owners to issue commands
    etype = commands.EVENT_MAP[event.event]
    if not event.data[etype]['author_association'] in ('COLLABORATOR', 'OWNER'):
        return

    await spawn(request, deferred_commands(event))


@routes.post("/")
async def main(request):
    """Handle requests."""

    try:
        # Get payload
        payload = await request.read()

        # Get authentication
        secret = os.environ.get("GH_SECRET")
        token = os.environ.get("GH_AUTH")
        bot = os.environ.get("GH_BOT")
        event = sansio.Event.from_http(request.headers, payload, secret=secret)

        # Handle ping
        if event.event == "ping":
            return web.Response(status=200)

        # Handle the event
        async with aiohttp.ClientSession() as session:
            gh = gh_aiohttp.GitHubAPI(session, bot, oauth_token=token, cache=cache)

            await router.dispatch(event, gh, request)

        return web.Response(status=200)
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return web.Response(status=500)


if __name__ == "__main__":
    app = web.Application()
    app.add_routes(routes)
    setup(app)

    port = os.environ.get("PORT")
    if port is not None:
        port = int(port)

    print(f'==== Starting Label Bot {__version__} ====')

    web.run_app(app, port=port)
