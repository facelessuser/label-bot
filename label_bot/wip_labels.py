"""Handle work in progress labels."""
import os
import sys
import traceback

DEFAULT = ('wip', 'work in progress', 'work-in-progress')


async def wip(event, gh, config):
    """Handle label events."""

    if event.state != 'open':
        return

    wip = False
    wip_list = set([label.lower() for label in config.get('wip', DEFAULT)])

    if config.get('labels_quick', True):
        # Grab the labels in this issue event.
        for name in event.labels:
            if name.lower() in wip_list:
                wip = True
                break
    else:
        # Grab the labels in this issue event.
        async for name in event.live_labels(gh):
            if name.lower() in wip_list:
                wip = True
                break

    await gh.post(
        event.statuses_url,
        {'sha': event.sha},
        data={
            "state": "pending" if wip else "success",
            "target_url": "https://github.com/gir-bot/label-bot",
            "description": "Work in progress" if wip else "Ready for review",
            "context": "{}/labels/wip".format(os.environ.get("GH_BOT"))
        }
    )


async def run(event, gh, config):
    """Run task."""

    try:
        await wip(event, gh, config)
        fail = False
    except Exception:
        traceback.print_exc(file=sys.stdout)
        fail = True

    if fail:
        await gh.post(
            event.statuses_url,
            {'sha': event.sha},
            data={
                "state": "failure",
                "target_url": "https://github.com/gir-bot/label-bot",
                "description": "Failed to complete",
                "context": "{}/labels/wip".format(os.environ.get("GH_BOT"))
            }
        )
