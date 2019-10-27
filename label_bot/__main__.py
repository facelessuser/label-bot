"""Main."""
import asyncio
from aiojobs.aiohttp import setup, spawn, get_scheduler_from_app
from bs4 import BeautifulSoup as bs  # noqa: N813
import aiohttp
import os
import sys
import cachetools
import traceback
import yaml
import base64
import re
from aiohttp import web
from gidgethub import routing, sansio
from gidgethub import aiohttp as gh_aiohttp
from . import wip_labels
from . import wildcard_labels
from . import sync_labels
from . import triage_labels
from . import review_labels
from . import util
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

__version__ = '1.0.0'

router = routing.Router()
routes = web.RouteTableDef()
cache = cachetools.LRUCache(maxsize=500)

sem = asyncio.Semaphore(1)

RE_COMMANDS = re.compile(
    r'''(?x)
    [ ]+(?:
        (?P<retrigger>retrigger[ ]+(?P<retrigger_task>auto-labels|wip|review|triage)) |
        (?P<sync>sync[ ]+labels)
    )\b
    ''',
    re.I
)


async def get_config(gh, contents_url, ref='master'):
    """Get label configuration file."""

    try:
        result = await gh.getitem(
            contents_url,
            {
                'path': '.github/labels.yml',
                'ref': ref
            }
        )
        content = base64.b64decode(result['content']).decode('utf-8')
        config = yaml.load(content, Loader=Loader)
    except Exception:
        traceback.print_exc(file=sys.stdout)
        config = {}

    return config


async def deferred_comment_task(event):
    """Defer handling of a comment."""

    async with sem:
        async with aiohttp.ClientSession() as session:
            token = os.environ.get("GH_AUTH")
            bot = os.environ.get("GH_BOT")
            gh = gh_aiohttp.GitHubAPI(session, bot, oauth_token=token, cache=cache)

            comment = await gh.getitem(event.data['comment']['url'], accept=sansio.accept_format(media="html"))
            soup = bs(comment['body_html'], 'html.parser')

            for el in soup.select('a.user-mention:contains("@{name}")[href$="/{name}"]'.format(name=bot)):
                payload = None
                pending = False
                module = None

                sib = el.next_sibling
                if not isinstance(sib, str):
                    continue

                m = RE_COMMANDS.match(sib)
                if m is None:
                    continue

                if m.group('retrigger'):
                    payload = {'repository': event.data['repository']}
                    issue = await gh.getitem(event.data['comment']['issue_url'])
                    event_type = 'issues'
                    key = 'issue'
                    if 'pull_request' in issue:
                        event_type = 'pull_request'
                        key = 'pull_request'
                        issue = await gh.getitem(issue['pull_request']['url'])
                    payload[key] = issue
                    action = m.group('retrigger_task')
                    if action == 'triage' and key == 'issue':
                        module = triage_labels
                    elif action == 'review' and key == 'pull_request':
                        module = review_labels
                    elif action == 'wip' and key == 'pull_request':
                        module = wip_labels
                    elif action == 'auto-labels' and key == 'pull_request':
                        pending = True
                        module = wildcard_labels
                    else:
                        continue

                elif m.group('sync'):
                    event_type = 'push'
                    branch = await gh.getitem(event.data['repository']['branches_url'], {'branch': 'master'})
                    payload = {'repository': event.data['repository'], 'after': branch['commit']['sha']}
                    pending = True
                    module = sync_labels

                else:
                    continue

                await gh.post(
                    event.data['repository']['issue_comment_url'] + '/reactions',
                    {'number': str(event.data['comment']['id'])},
                    data={'content': 'eyes'},
                    accept=','.join([sansio.accept_format(), 'application/vnd.github.squirrel-girl-preview+json'])
                )
                event = util.Event(event_type, payload)
                if pending:
                    await module.pending(event, gh)
                await get_scheduler_from_app(app).spawn(deferred_task(module.run, event, event.sha))


async def deferred_task(function, event, ref):
    """Defer the event work."""

    async with sem:
        async with aiohttp.ClientSession() as session:
            token = os.environ.get("GH_AUTH")
            bot = os.environ.get("GH_BOT")
            gh = gh_aiohttp.GitHubAPI(session, bot, oauth_token=token, cache=cache)

            await asyncio.sleep(1)
            config = await get_config(gh, event.contents_url, ref)
            await function(event, gh, config)


async def handle_pull_actions(event, gh, config):
    """Handle non label specific actions."""

    await wip_labels.run(event, gh, config)
    await review_labels.run(event, gh, config)
    await wildcard_labels.pending(event, gh)
    await asyncio.sleep(1)
    await wildcard_labels.run(event, gh, config)


@router.register("pull_request", action="labeled")
async def pull_labeled(event, gh, request, *args, **kwargs):
    """Handle pull request labeled event."""

    event = util.Event(event.event, event.data)
    config = await get_config(gh, event.contents_url, event.sha)
    await wip_labels.run(event, gh, config)


@router.register("pull_request", action="unlabeled")
async def pull_unlabeled(event, gh, request, *args, **kwargs):
    """Handle pull request unlabeled event."""

    event = util.Event(event.event, event.data)
    config = await get_config(gh, event.contents_url, event.sha)
    await wip_labels.run(event, gh, config)


@router.register("pull_request", action="reopened")
async def pull_reopened(event, gh, request, *args, **kwargs):
    """Handle pull reopened events."""

    event = util.Event(event.event, event.data)
    await wildcard_labels.pending(event, gh)
    await spawn(request, deferred_task(handle_pull_actions, event, event.sha))


@router.register("pull_request", action="opened")
async def pull_opened(event, gh, request, *args, **kwargs):
    """Handle pull opened events."""

    event = util.Event(event.event, event.data)
    await wildcard_labels.pending(event, gh)
    await spawn(request, deferred_task(handle_pull_actions, event, event.sha))


@router.register("pull_request", action="synchronize")
async def pull_synchronize(event, gh, request, *args, **kwargs):
    """Handle pull synchronization events."""

    event = util.Event(event.event, event.data)
    await wildcard_labels.pending(event, gh)
    await spawn(request, deferred_task(handle_pull_actions, event, event.sha))


@router.register("issues", action="opened")
async def issues_opened(event, gh, request, *args, **kwargs):
    """Handle issues open events."""

    event = util.Event(event.event, event.data)
    config = await get_config(gh, event.contents_url)
    await triage_labels.run(event, gh, config)


@router.register('push', ref='refs/heads/master')
async def push(event, gh, request, *args, **kwargs):
    """Handle push events on master."""

    event = util.Event(event.event, event.data)
    await sync_labels.pending(event, gh)
    await spawn(request, deferred_task(sync_labels.run, event, event.sha))


@router.register('issue_comment', action="created")
async def issue_comment_created(event, gh, request, *args, **kwargs):
    """Handle issue comment created."""

    await spawn(request, deferred_comment_task(event))


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

            await asyncio.sleep(1)
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

    web.run_app(app, port=port)
