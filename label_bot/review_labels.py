"""Review labels."""
import os
from gidgethub import sansio


async def review(event, gh, config):
    """Add review labels."""

    review_label = config.get('review_label', 'needs-review')

    # Nothing to add
    if not review_label:
        return

    skip = set([label.lower() for label in config.get('review_skip', ['skip-review'])])
    skip.add(review_label.lower())

    # If the label is already present, or the skip label is present, then there is nothing to do.
    for name in event.labels:
        if name.lower() == skip:
            return

    await gh.post(
        event.issue_labels_url,
        {'number': event.number},
        data={'labels': [review_label]},
        accept=','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
    )


async def run(event, gh, config):
    """Run the task."""

    try:
        await review(event, gh, config)
        success = True
    except Exception:
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
