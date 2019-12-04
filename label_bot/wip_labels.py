"""Handle work in progress labels."""
import sys
import traceback
from . import util

DEFAULT = ('wip', 'work in progress', 'work-in-progress')


async def wip(event, gh, config):
    """Handle label events."""

    wip = False
    wip_list = set([label.lower() for label in config.get('wip', DEFAULT)])

    # Grab the labels in this issue event.
    async for name in event.get_issue_labels(gh):
        if name.lower() in wip_list:
            wip = True
            break

    print('WIP: ', str(wip))

    await event.set_status(
        gh,
        util.EVT_PENDING if wip else util.EVT_SUCCESS,
        'labels/wip',
        "Work in progress" if wip else "Ready for review"
    )


async def run(event, gh, config, **kwargs):
    """Run task."""

    print(f'WIP: {event.full_name}')

    try:
        if config.get('error', ''):
            raise Exception(config['error'])
        await wip(event, gh, config)
        fail = False
    except Exception:
        traceback.print_exc(file=sys.stdout)
        fail = True

    if fail:
        await event.set_status(
            gh,
            util.EVT_FAILURE,
            'labels/wip',
            'Failed to complete task'
        )
