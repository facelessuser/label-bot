"""Handle work in progress labels."""
import os
from gidgethub import sansio

DEFAULT = ('wip', 'work in progress', 'work-in-progress')


async def wip(event, gh, config):
    """Handle label events."""

    action = event.data['action']

    if event.data['pull_request']['state'] != 'open':
        return

    wip = False
    wip_list = set([label.lower() for label in config.get('wip', ['wip', 'work in progress', 'work-in-progress'])])

    if action in ('reopened', 'synchronize'):
        # Physically get the latest labels for a reopened and synchronize event.
        url = event.data['pull_request']['issue_url'] + '/labels'
        accept = ','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
        async for label in gh.getiter(url, accept=accept):
            name = label['name'].lower()
            if name in wip_list:
                wip = True
                break

    else:
        # Grab the labels in this issue event.
        for label in event.data['pull_request']['labels']:
            name = label['name'].encode('utf-16', 'surrogatepass').decode('utf-16').lower()
            if name in set([label.lower() for label in config.get('wip', DEFAULT)]):
                wip = True
                break

    await gh.post(
        event.data['pull_request']['statuses_url'],
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
        wip(event, gh, config)
        fail = False
    except Exception:
        fail = True

    if fail:
        await gh.post(
            event.data['pull_request']['statuses_url'],
            data={
                "state": "failure",
                "target_url": "https://github.com/gir-bot/label-bot",
                "description": "Failed to complete",
                "context": "{}/labels/wip".format(os.environ.get("GH_BOT"))
            }
        )
