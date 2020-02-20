"""Utilities."""
import asyncio
import base64
import yaml
import traceback
import sys
import os
from gidgethub import sansio, InvalidField
try:
    from yaml import CLoader as Loader
except ImportError:
    from yaml import Loader

LABEL_HEADER = ','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
REACTION_HEADER = ','.join([sansio.accept_format(), 'application/vnd.github.squirrel-girl-preview+json'])
HTML_HEADER = sansio.accept_format(media="html")

SINGLE_VALUES = {
    'brace_expansion', 'extended_glob', 'case_insensitive',
    'triage_label', 'review_label', 'delete_labels'
}

LIST_VALUES = {
    'labels', 'rules', 'wip', 'lgtm_remove', 'lgtm_add_issue',
    'lgtm_add_pull_request', 'triage_skip', 'triage_remove',
    'review_skip', 'review_remove'
}

DICT_VALUES = {'colors'}

EVT_SUCCESS = "success"
EVT_FAILURE = "failure"
EVT_ERROR = "error"
EVT_PENDING = "pending"


class Event:
    """Event object."""

    def __init__(self, event_type, data, local_ref=False):
        """Initialize."""

        self.event = event_type
        self.local_ref = local_ref
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
        self.full_name = data['repository']['full_name']
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

    def merge_config(self, master_config, config):
        """Merge master config and local config."""

        # Normalize configuration files in relation to LGTM options.
        # Use separate options for issue and pull request.
        for cfg in (master_config, config):
            if 'lgtm_add' in cfg:
                cfg['lgtm_add_issue'] = cfg['lgtm_add'].get('issue', [])
                cfg['lgtm_add_pull_request'] = cfg['lgtm_add'].get('pull_request', [])

        if not master_config:
            return config

        for key, value in config.items():
            if key in SINGLE_VALUES:
                master_config[key] = value
            elif key in LIST_VALUES and key in master_config:
                master_config[key].extend(value)
            elif key in DICT_VALUES and key in master_config:
                for k, v in value.items():
                    master_config[key][k] = v
            else:
                master_config[key] = value
        return master_config

    async def get_config(self, gh):
        """Get label configuration file."""

        await asyncio.sleep(1)
        config = {}
        try:
            result = await gh.getitem(
                self.contents_url,
                {
                    'path': '.github/labels.yml',
                    'ref': self.sha if self.local_ref else 'master'
                }
            )
            content = base64.b64decode(result['content']).decode('utf-8')
            config = yaml.load(content, Loader=Loader)
            template = config.get('template', '')
            if template:
                user, repo, path, ref = template.split(':')
                result = await gh.getitem(
                    'https://api.github.com/repos/{user}/{repo}/contents/{path}/{?ref}',
                    {
                        'user': user,
                        'repo': repo,
                        'path': path,
                        'ref': ref
                    }
                )
                content = base64.b64decode(result['content']).decode('utf-8')
                template_config = yaml.load(content, Loader=Loader)
                config = self.merge_config(template_config, config)
        except Exception:
            traceback.print_exc(file=sys.stdout)
            config = {'error': str(traceback.format_exc())}

        return config

    async def set_status(self, gh, status, context, msg):
        """Set status."""

        print(os.environ.get("GH_BOT_LINK", "https://github.com/facelessuser/label-bot"))
        await gh.post(
            self.statuses_url,
            {'sha': self.sha},
            data={
                "state": status,
                "target_url": f'{os.environ.get("GH_BOT_LINK", "https://github.com/facelessuser/label-bot")}',
                "description": msg,
                "context": f'{os.environ.get("GH_BOT")}/{context}'
            }
        )

    async def post_comment(self, gh, comment):
        """Post comment."""

        await gh.post(
            self.issues_comments_url,
            {"number": self.number},
            data={"body": comment}
        )

    async def get_repo_labels(self, gh):
        """Get the repository labels."""

        count = 0
        async for label in gh.getiter(self.labels_url, accept=LABEL_HEADER):
            count += 1
            if (count % 30) == 0:
                await asyncio.sleep(1)
            yield label

    async def update_repo_label(self, gh, old_name, new_name, color, description):
        """Update the repository label."""

        try:
            await gh.patch(
                self.labels_url,
                {'name': old_name},
                data={'new_name': new_name, 'color': color, 'description': description},
                accept=LABEL_HEADER
            )
        except InvalidField as e:
            # Can occur if name already exists, ignore such errors
            if "Validation Failed for 'name'" not in str(e):
                raise

    async def remove_repo_label(self, gh, label):
        """Remove repository label."""

        try:
            await gh.delete(
                self.labels_url,
                {'name': label},
                accept=LABEL_HEADER
            )
        except InvalidField as e:
            # Likely to occur if name doesn't exists, ignore such errors
            if "Validation Failed for 'name'" not in str(e):
                raise

    async def add_repo_label(self, gh, name, color, description):
        """Add repository label."""

        try:
            await gh.post(
                self.labels_url,
                data={'name': name, 'color': color, 'description': description},
                accept=LABEL_HEADER
            )
        except InvalidField as e:
            # Can occur if name already exists, ignore such errors
            if "Validation Failed for 'name'" not in str(e):
                raise

    async def get_issue_labels(self, gh):
        """Get the issue's labels."""

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

    async def add_issue_labels(self, gh, labels):
        """Add issue labels."""

        if labels:
            await gh.post(
                self.issue_labels_url,
                {'number': self.number},
                data={'labels': labels},
                accept=LABEL_HEADER
            )

    async def remove_issue_labels(self, gh, labels):
        """Remove issue labels."""

        count = 0
        for label in labels:
            count += 1
            if (count % 2) == 0:
                await asyncio.sleep(1)

            await gh.delete(
                self.issue_labels_url,
                {'number': self.number, 'name': label},
                accept=LABEL_HEADER
            )
