"""Handle work in progress labels."""


async def wip(event, gh, config):
    """Handle label events."""

    if event.data['pull_request']['state'] != 'open':
        return

    wip = False
    wip_list = set([label.lower() for label in config.get('wip', ['wip', 'work in progress', 'work-in-progress'])])

    url = event.data['pull_request']['issue_url'] + '/labels'
    accept = 'application/vnd.github.symmetra-preview+json'
    async for label in gh.getiter(url, accept=accept):
        name = label['name'].lower()
        if name in wip_list:
            wip = True
            break

    await gh.post(
        event.data['pull_request']['statuses_url'],
        data={
            "state": "pending" if wip else "success",
            "target_url": "https://github.com/isaac-muse/do-not-merge",
            "description": "Work in progress" if wip else "Ready for review",
            "context": "wip"
        }
    )
