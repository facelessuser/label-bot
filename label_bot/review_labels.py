"""Review labels."""
import os
import traceback
import sys
from . import util

DEFAULT = 'needs-review'
DEFAULT_SKIP = ['skip-review']


async def review(event, gh, config):
    """Add review labels."""

    review_label = config.get('review_label', DEFAULT)

    # Nothing to add
    if not review_label:
        return

    skip = set([label.lower() for label in config.get('review_skip', DEFAULT_SKIP)])
    skip.add(review_label.lower())

    quick = config.get('quick_labels', True)
    if quick:
        current_labels = event.labels[:]
    else:
        current_labels = [x async for x in event.live_labels(gh)]

    # If the label is already present, or the skip label is present, then there is nothing to do.
    for name in current_labels:
        if name.lower() in skip:
            return

    current_labels.append(review_label)
    event.labels.clear()
    event.labels.extend(current_labels)

    await gh.post(
        event.issue_labels_url,
        {'number': event.number},
        data={'labels': [review_label]},
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
