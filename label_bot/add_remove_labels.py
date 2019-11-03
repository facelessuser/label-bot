"""Looks good to me command."""
import traceback
import sys


async def run(event, gh, config, labels=None, remove=False, **kwargs):
    """Run the task."""

    try:
        if config.get('error', ''):
            raise Exception(config['error'])

        if not labels:
            return

        await add_remove(event, gh, config, labels, remove)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    if not success:
        await event.post_comment(
            gh,
            'Oops! There was a problem {} some of the labels.'.format('adding' if not remove else 'removing')
        )


async def add_remove(event, gh, config, labels, remove_mode):
    """Remove specified labels, and set desired labels if specified."""

    label_list = set([name['name'].lower() for name in config.get('labels', [])])
    labels = {label.lower(): label for label in labels}

    # Remove labels not currently tracked
    delete = []
    for label in labels.keys():
        if label not in label_list:
            delete.append(label)
    for label in delete:
        del labels[label]

    if not labels:
        return

    add = []
    remove = []
    async for name in event.get_issue_labels(gh):
        low = name.lower()
        if not remove_mode and low in labels:
            del labels[low]
        elif remove_mode and low in labels:
            remove.append(labels[low])

    if not remove_mode:
        add = [x for x in labels.values()]

    await event.remove_issue_labels(gh, remove)
    await event.add_issue_labels(gh, add)
