"""Triage labels."""

async def triage(event, gh, config):
    """Add triage labels."""

    if 'pull_request' in event.data:
        labels = config.get('triage_issue_labels', ['needs-review'])
        url = event.data['pull_request']['issue_url'] + '/labels'
    else:
        labels = config.get('triage_pull_request_labels', ['triage'])
        url = event.data['issue']['labels_url'].replace('{/name}', '')

    if labels:
        await gh.post(url, data={'labels': labels}, accept='application/vnd.github.symmetra-preview+json')
