"""Looks good to me command."""
import asyncio
import traceback
import sys
from . import util


async def run(event, gh, config, key=None):
    """Run the task."""

    try:
        await lgtm(event, gh, config, key)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    if not success:
        await gh.post(
            event.issues_comments_url,
            {"number": event.number},
            data={"body": "Oops! There was a problem transitioning the issue."}
        )


async def lgtm(event, gh, config, key):
    """Remove specified labels, and set desired labels if specified."""

    keys = config.get('lgtm_add', {})
    add_labels = {}
    remove_labels = {}
    add = []
    remove = []

    if key and key in keys:
        for name in keys[key]:
            add_labels[name.lower()] = name

    if event.event == 'pull_request':
        for name in config.get('lgtm_pull_request_remove', []):
            remove_labels[name.lower()] = name
    else:
        for name in config.get('lgtm_issue_remove', []):
            remove_labels[name.lower()] = name

    async for name in event.live_labels(gh):
        low = name.lower()
        if low in add_labels:
            del add_labels[low]
        if low in remove_labels:
            remove.append(remove_labels[low])

    add = [x for x in add_labels.values()]

    if add:
        await gh.post(
            event.issue_labels_url,
            {'number': event.number},
            data={'labels': add},
            accept=util.LABEL_HEADER
        )

    count = 0
    for label in remove:
        count += 1
        if (count % 2) == 0:
            await asyncio.sleep(1)

        await gh.delete(
            event.issue_labels_url,
            {'number': event.number, 'name': label},
            accept=util.LABEL_HEADER
        )
