"""Triage labels."""
from gidgethub import sansio


async def triage(event, gh, config):
    """Add triage labels."""

    key = 'pull_request' if 'pull_request' in event.data else 'issue'
    skip = config.get('triage_skip', 'skip-triage').lower()
    for label in event.data[key]['labels']:
        name = label['name'].encode('utf-16', 'surrogatepass').decode('utf-16').lower()
        if name == skip:
            return

    if 'pull_request' in event.data:
        labels = config.get('triage_issue_labels', ['needs-review'])
        url = event.data['pull_request']['issue_url'] + '/labels'
    else:
        labels = config.get('triage_pull_request_labels', ['triage'])
        url = event.data['issue']['labels_url'].replace('{/name}', '')

    if labels:
        await gh.post(
            url,
            data={'labels': labels},
            accept=','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
        )
