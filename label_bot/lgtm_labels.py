"""Looks good to me command."""
import traceback
import sys


async def run(event, gh, config):
    """Run the task."""

    try:
        if config.get('error', ''):
            raise Exception(config['error'])
        await lgtm(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    if not success:
        await event.post_comment(gh, 'Oops! There was a problem transitioning the issue.')


async def lgtm(event, gh, config, **kwargs):
    """Remove specified labels, and set desired labels if specified."""

    key = 'pull_request' if event.event == 'pull_request' else 'issue'
    add_labels = {value.lower(): value for value in config.get('lgtm_add', {}).get(key, [])}
    remove_labels = {label.lower(): label for label in config.get('lgtm_remove', [])}

    add = []
    remove = []

    async for name in event.get_issue_labels(gh):
        low = name.lower()
        if low in add_labels:
            del add_labels[low]
        if low in remove_labels:
            remove.append(remove_labels[low])

    add = [x for x in add_labels.values()]

    await event.remove_issue_labels(gh, remove)
    await event.add_issue_labels(gh, add)
