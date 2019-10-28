"""Utilities."""
import asyncio
import base64
import yaml
import traceback
import sys
from gidgethub import sansio
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

LABEL_HEADER = ','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
REACTION_HEADER = ','.join([sansio.accept_format(), 'application/vnd.github.squirrel-girl-preview+json'])
HTML_HEADER = sansio.accept_format(media="html")


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
            self.sha = 'master'
            self.state = data['issue']['state']
            self.labels = [self.decode_label(label['name']) for label in data['issue']['labels']]
            self.base = None
            self.head = None
            self.number = str(data['issue']['number'])
        self.branches_url = data['repository']['branches_url']
        self.issues_url = data['repository']['issues_url']
        self.issues_comments_url = self.issues_url + '/comments'
        self.issue_labels_url = self.issues_url + '/labels{/name}'
        self.statuses_url = data['repository']['statuses_url']
        self.compare_url = data['repository']['compare_url']
        self.labels_url = data['repository']['labels_url']
        self.contents_url = data['repository']['contents_url'] + '{?ref}'

    def decode_label(self, name):
        """Decode label."""

        return name.encode('utf-16', 'surrogatepass').decode('utf-16')

    async def live_labels(self, gh):
        """Get the current, live labels."""

        count = 0
        accept = ','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
        async for label in gh.getiter(self.issue_labels_url, {'number': self.number}, accept=accept):

            # Not sure how many get returned before it must page, so sleep for
            # one second on the arbitrary value of 20. That is a lot of labels for
            # one issue, so it is probably not going to trigger often.
            count += 1
            if (count % 20) == 0:
                await asyncio.sleep(1)

            yield label['name']

    async def get_config(self, gh):
        """Get label configuration file."""

        await asyncio.sleep(1)
        try:
            result = await gh.getitem(
                self.contents_url,
                {
                    'path': '.github/labels.yml',
                    'ref': self.sha
                }
            )
            content = base64.b64decode(result['content']).decode('utf-8')
            config = yaml.load(content, Loader=Loader)
        except Exception:
            traceback.print_exc(file=sys.stdout)
            config = {}

        return config
