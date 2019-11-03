"""Review labels."""
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

    async for name in event.get_issue_labels(gh):
        low = name.lower()
        if low in skip:
            return
        if low in add_labels:
            del add_labels[low]
        if low in remove_labels:
            remove.append(remove_labels[low])

    add = [x for x in add_labels.values()]

    await event.remove_issue_labels(gh, remove)
    await event.add_issue_labels(gh, add)


async def run(event, gh, config, **kwargs):
    """Run the task."""

    try:
        if config.get('error', ''):
            raise Exception(config['error'])
        await review(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    await event.set_status(
        gh,
        util.EVT_SUCCESS if success else util.EVT_FAILURE,
        'labels/review',
        "Task completed" if success else "Failed to complete task"
    )
