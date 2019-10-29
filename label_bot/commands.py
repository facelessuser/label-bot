"""Handler of commands via issue comments/bodies."""
import asyncio
import re
from bs4 import BeautifulSoup
from . import wip_labels
from . import wildcard_labels
from . import sync_labels
from . import triage_labels
from . import review_labels
from . import lgtm_labels
from . import util
from collections import namedtuple

EVENT_MAP = {
    'issue_comment': 'comment',
    'pull_request': 'pull_request',
    'issues': 'issue'
}

RE_COMMANDS = re.compile(
    r'''(?x)
    [ ]+(?:
        (?P<lgtm>lgtm(?:[ ]*,[ ]*(?P<lgtm_key>[a-z][-a-z0-9_]*))?) |
        (?P<retrigger>retrigger[ ]+(?P<retrigger_task>auto-labels|wip|review|triage|all)) |
        (?P<sync>sync[ ]+labels)
    )\b
    ''',
    re.I
)


class Command(namedtuple('Command', ['command', 'event', 'pending', 'live', 'kwargs'])):
    """Command."""


async def command_retrigger(event, action, gh):
    """Handle retrigger command."""

    # These events shouldn't be run on a closed issue.
    if event.data['issue']['state'] != 'open':
        return None

    await asyncio.sleep(1)
    payload = {'repository': event.data['repository']}
    issue = await gh.getitem(event.data['comment']['issue_url'])
    event_type = 'issues'
    key = 'issue'
    if 'pull_request' in issue:
        event_type = 'pull_request'
        key = 'pull_request'
        issue = await gh.getitem(issue['pull_request']['url'])
    payload[key] = issue

    if action in ('triage', 'all') and key == 'issue':
        command = Command(triage_labels.run, util.Event(event_type, payload), None, False, {})
    elif action == 'all' and key == 'pull_request':
        command = Command(run_all_pull_actions, util.Event(event_type, payload), None, False, {})
    elif action == 'review' and key == 'pull_request':
        command = Command(review_labels.run, util.Event(event_type, payload), None, True, {})
    elif action == 'wip' and key == 'pull_request':
        command = Command(wip_labels.run, util.Event(event_type, payload), None, True, {})
    elif action == 'auto-labels' and key == 'pull_request':
        command = Command(wildcard_labels.run, util.Event(event_type, payload), wildcard_labels.pending, True, {})
    else:
        command = None
    return command


async def command_sync(event, gh):
    """Handle sync command."""

    await asyncio.sleep(1)
    event_type = 'push'
    branch = await gh.getitem(event.data['repository']['branches_url'], {'branch': 'master'})
    payload = {'repository': event.data['repository'], 'after': branch['commit']['sha']}
    return Command(sync_labels.run, util.Event(event_type, payload), sync_labels.pending, False)


async def command_lgtm(event, key, gh):
    """Handle "looks good to me" command."""

    if event.data['issue']['state'] != 'open':
        return None

    kwargs = {}
    if key:
        kwargs['key'] = key

    await asyncio.sleep(1)
    payload = {'repository': event.data['repository']}
    issue = await gh.getitem(event.data['comment']['issue_url'])
    event_type = 'issues'
    key = 'issue'
    if 'pull_request' in issue:
        event_type = 'pull_request'
        key = 'pull_request'
        issue = await gh.getitem(issue['pull_request']['url'])
    payload[key] = issue
    return Command(lgtm_labels.run, util.Event(event_type, payload), None, False, kwargs)


async def run_all_pull_actions(event, gh, config):
    """Run all label specific actions."""

    await wip_labels.run(event, gh, config)
    await review_labels.run(event, gh, config)
    await wildcard_labels.pending(event, gh)
    await asyncio.sleep(1)
    await wildcard_labels.run(event, gh, config)


async def react_to_command(event, gh):
    """React to command."""

    etype = EVENT_MAP[event.event]
    if etype == 'comment':
        url = event.data['repository']['issue_comment_url'] + '/reactions'
        url_values = {'number': str(event.data['comment']['id'])}
    elif etype == 'pull_request':
        url = event.data[etype]['issue_url'] + '/reactions'
        url_values = {}
    else:
        url = event.data[etype]['url'] + '/reactions'
        url_values = {}

    await gh.post(url, url_values, data={'content': 'eyes'}, accept=util.REACTION_HEADER)


async def run(event, gh, bot):
    """Handle commands."""

    reacted = False

    etype = EVENT_MAP[event.event]
    comment = await gh.getitem(event.data[etype]['url'], accept=util.HTML_HEADER)
    soup = BeautifulSoup(comment['body_html'], 'html.parser')

    for el in soup.select('a.user-mention:contains("@{name}")[href$="/{name}"]'.format(name=bot)):

        sib = el.next_sibling
        if not isinstance(sib, str):
            continue

        m = RE_COMMANDS.match(sib)
        if m is None:
            continue

        if etype == 'comment' and m.group('retrigger'):
            cmd = await command_retrigger(event, m.group('retrigger_task'), gh)

        elif m.group('sync'):
            cmd = await command_sync(event, gh)

        elif m.group('lgtm'):
            cmd = await command_lgtm(event, m.group('lgtm_key'), gh)

        else:
            continue

        if cmd is None:
            continue

        if not reacted:
            await react_to_command(event, gh)
            reacted = True

        yield cmd
