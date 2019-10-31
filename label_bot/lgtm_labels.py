"""Looks good to me command."""
import asyncio
import traceback
import sys
from . import util


async def run(event, gh, config):
    """Run the task."""

    try:
        await lgtm(event, gh, config)
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


async def lgtm(event, gh, config, **kwargs):
    """Remove specified labels, and set desired labels if specified."""

    key = 'pull_request' if event.event == 'pull_request' else 'issue'
    add_labels = {value.lower(): value for value in config.get('lgtm_add', {}).get(key, [])}
    remove_labels = {label.lower(): label for label in config.get('lgtm_remove', [])}

    add = []
    remove = []

    async for name in event.live_labels(gh):
        low = name.lower()
        if low in add_labels:
            del add_labels[low]
        if low in remove_labels:
            remove.append(remove_labels[low])

    add = [x for x in add_labels.values()]

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

    if add:
        await gh.post(
            event.issue_labels_url,
            {'number': event.number},
            data={'labels': add},
            accept=util.LABEL_HEADER
        )
