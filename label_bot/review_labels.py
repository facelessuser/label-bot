"""Review labels."""
import asyncio
import os
import traceback
import sys
from . import util

DEFAULT = 'needs-review'
DEFAULT_SKIP = ['skip-review']
DEFAULT_REMOVE = []


async def review(event, gh, config):
    """Add review labels."""

    review_label = config.get('review_label', DEFAULT)
    add_labels = {review_label: review_label.lower()}
    remove_labels = {label.lower(): label for label in config.get('review_remove', DEFAULT_REMOVE)}
    skip = set([label.lower() for label in config.get('review_skip', DEFAULT_SKIP)])

    add = []
    remove = []

    # Nothing to add
    if not review_label:
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


async def run(event, gh, config):
    """Run the task."""

    try:
        await review(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    await gh.post(
        event.statuses_url,
        {'sha': event.sha},
        data={
            "state": "success" if success else "failure",
            "target_url": "https://github.com/gir-bot/label-bot",
            "description": "Task completed" if success else "Failed to complete",
            "context": "{}/labels/review".format(os.environ.get("GH_BOT"))
        }
    )
