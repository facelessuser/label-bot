"""Triage labels."""
import traceback
import sys

DEFAULT = 'triage'
DEFAULT_SKIP = ['skip-triage']
DEFAULT_REMOVE = []


async def run(event, gh, config, **kwargs):
    """Run task."""

    print(f'TRIAGE: {event.full_name}')

    try:
        if config.get('error', ''):
            raise Exception(config['error'])
        await triage(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    if not success:
        await event.post_comment(gh, 'Oops! It appears I am having difficulty marking this issue for triage.')


async def triage(event, gh, config):
    """Add triage labels."""

    triage_label = config.get('triage_label', DEFAULT)
    add_labels = {triage_label.lower(): triage_label}
    remove_labels = {label.lower(): label for label in config.get('triage_remove', DEFAULT_REMOVE)}
    skip = set([label.lower() for label in config.get('triage_skip', DEFAULT_SKIP)])

    add = []
    remove = []

    # Nothing to add
    if not triage_label:
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

    print('TRIAGE: Removing: ', str(remove))
    print('TRIAGE: Adding: ', str(add))

    await event.remove_issue_labels(gh, remove)
    await event.add_issue_labels(gh, add)
