"""Triage labels."""
from gidgethub import sansio
import traceback
import sys


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

    triage_label = config.get('triage_label', 'triage')

    # Nothing to add
    if not triage_label:
        return

    skip = set([label.lower() for label in config.get('triage_skip', ['skip-triage'])])
    skip.add(triage_label.lower())

    quick = config.get('quick_labels', True)
    if quick:
        current_labels = event.labels[:]
    else:
        current_labels = [x async for x in event.live_labels(gh)]

    # If the label is already present, or the skip label is present, then there is nothing to do.
    for name in current_labels:
        if name.lower() in skip:
            return

    current_labels.append(triage_label)
    event.labels.clear()
    event.labels.extend(current_labels)

    await gh.post(
        event.issue_labels_url,
        {'number': event.number},
        data={'labels': [triage_label]},
        accept=','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
    )
