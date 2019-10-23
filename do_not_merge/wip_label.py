"""Handle work in progress labels."""

async def wip(event, gh, config):
    """Handle label events."""

    if event.data['pull_request']['state'] != 'open':
        return

    wip = False
    for label in event.data['pull_request']['labels']:
        name = label['name'].encode('utf-16', 'surrogatepass').decode('utf-16').lower()
        if name in set([label.lower() for label in config.get('wip', [])]):
            wip = True
            break

    print('WIP: ', str(wip))

    await gh.post(
        event.data['pull_request']['statuses_url'],
        data={
          "state": "pending" if wip else "success",
          "target_url": "https://github.com/isaac-muse/do-not-merge",
          "description": "Work in progress" if wip else "Ready for review",
          "context": "wip"
        }
    )
