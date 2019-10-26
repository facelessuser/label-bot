"""Utilities."""


class Event:
    """Event object."""

    def __init__(self, event):
        """Initialize."""

        self.event = event.event
        if self.event == 'push':
            self.sha = event.data['after']
            self.state = None
            self.labels = None
            self.base = None
            self.head = None
            self.number
        elif self.event == 'pull_request':
            self.sha = event.data['pull_request']['head']['sha']
            self.state = event.data['pull_request']['state']
            self.labels = [self.decode_label(label['name']) for label in event.data['pull_request']['labels']]
            self.base = event.data['pull_request']['base']['label']
            self.head = event.data['pull_request']['head']['label']
            self.number = event.data['issue']['number']
        elif self.event == 'issues':
            self.sha = None
            self.state = event.data['issue']['state']
            self.labels = [self.decode_label(label) for label in event.data['issues']['labels']]
            self.base = None
            self.head = None
            self.number = event.data['pull_request']['number']
        self.issues_url = event.data['repository']['issues_url']
        self.issue_labels_url = self.issues_url + '/labels'
        self.statuses_url = event.data['repository']['statuses_url']
        self.compare_url = event.data['repository']['compare_url']
        self.labels_url = event.data['repository']['labels_url']
        self.comments_url = event.data['repository']['comments_url']
        self.contents_url = event.data['repository']['contents_url'] + '{?ref}'

    def decode_label(self, name):
        """Decode label."""

        return name.encode('utf-16', 'surrogatepass').decode('utf-16')
