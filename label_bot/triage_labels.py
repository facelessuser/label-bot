"""Triage labels."""
import asyncio
import traceback
import sys
from . import util

DEFAULT = 'triage'
DEFAULT_SKIP = ['skip-triage']
DEFAULT_REMOVE = []


async def run(event, gh, config):
    """Run task."""

    try:
        await triage(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    if not success:
        await gh.post(
            event.issues_comments_url,
            {'number': event.number},
            data={'body': 'Oops! It appears I am having difficulty marking this issue for triage.'}
        )


async def triage(event, gh, config):
    """Add triage labels."""

    triage_label = config.get('triage_label', DEFAULT)
    add_labels = {triage_label: triage_label.lower()}
    remove_labels = {label.lower(): label for label in config.get('triage_remove', DEFAULT_REMOVE)}
    skip = set([label.lower() for label in config.get('triage_skip', DEFAULT_SKIP)])

    add = []
    remove = []

    # Nothing to add
    if not triage_label:
        return

    async for name in event.live_labels(gh):
        low = name.lower()
        if low in skip:
            return
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
