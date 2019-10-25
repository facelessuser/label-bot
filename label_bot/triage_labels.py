"""Triage labels."""
from gidgethub import sansio


async def run(event, gh, config):
    """Run task."""

    try:
        await triage(event, gh, config)
        success = True
    except Exception:
        success = False

    if not success:
        gh.post(
            event.data['issue']['comments_url'],
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

    # If the label is already present, or the skip label is present, then there is nothing to do.
    for label in event.data['issue']['labels']:
        name = label['name'].encode('utf-16', 'surrogatepass').decode('utf-16').lower()
        if name == skip:
            return

    await gh.post(
        event.data['issue']['labels_url'],
        data={'labels': [triage_label]},
        accept=','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
    )
