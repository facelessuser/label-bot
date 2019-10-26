"""Utilities."""


class Event:
    """Event object."""

    def __init__(self, event_type, data):
        """Initialize."""

        self.event = event_type
        if self.event == 'push':
            self.sha = data['after']
            self.state = None
            self.labels = None
            self.base = None
            self.head = None
            self.number = None
        elif self.event == 'pull_request':
            self.sha = data['pull_request']['head']['sha']
            self.state = data['pull_request']['state']
            self.labels = [self.decode_label(label['name']) for label in data['pull_request']['labels']]
            self.base = data['pull_request']['base']['label']
            self.head = data['pull_request']['head']['label']
            self.number = str(data['pull_request']['number'])
        elif self.event == 'issues':
            self.sha = None
            self.state = data['issue']['state']
            self.labels = [self.decode_label(label) for label in data['issues']['labels']]
            self.base = None
            self.head = None
            self.number = str(data['issue']['number'])
        self.branches_url = data['repository']['branches_url']
        self.issues_url = data['repository']['issues_url']
        self.issue_labels_url = self.issues_url + '/labels'
        self.statuses_url = data['repository']['statuses_url']
        self.compare_url = data['repository']['compare_url']
        self.labels_url = data['repository']['labels_url']
        self.comments_url = data['repository']['comments_url']
        self.contents_url = data['repository']['contents_url'] + '{?ref}'

    def decode_label(self, name):
        """Decode label."""

        return name.encode('utf-16', 'surrogatepass').decode('utf-16')
