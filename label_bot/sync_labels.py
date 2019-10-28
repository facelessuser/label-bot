"""Label syncing."""
import asyncio
from gidgethub import sansio
from collections import namedtuple
import os
import re
import traceback
import sys

RE_VALID_COLOR = re.compile('#[a-fA-F0-9]{6}')


class LabelEdit(namedtuple('LabelEdit', ['old', 'new', 'color', 'description', 'modified'])):
    """Label Edit tuple."""


def _validate_str(name):
    """Validate name."""

    if not isinstance(name, str):
        raise TypeError("Key value is not of type 'str', type '{}' received instead".format(type(name)))


def _validate_color(color):
    """Validate color."""

    _validate_str(color)

    if RE_VALID_COLOR.match(color) is None:
        raise ValueError('{} is not a valid color'.format(color))


def _resolve_color(color, colors):
    """Parse color."""

    if RE_VALID_COLOR.match(color) is None:
        color = colors[color]
    return color


def _parse_colors(config):
    """Get colors."""

    colors = {}
    for name, color in config.get('colors', {}).items():
        try:
            _validate_color(color)
            _validate_str(name)
            if name in colors:
                raise ValueError("The name '{}' is already present in the color list".format(name))
            colors[name] = color[1:]
        except Exception:
            traceback.print_exc(file=sys.stdout)
    return colors


def _find_label(labels, label, label_color, label_description):
    """Find label."""

    edit = None
    for value in labels:
        name = value['name']
        old_name = value.get('renamed', name)

        if label.lower() != old_name.lower():
            if label.lower() == name.lower():
                old_name = name
            else:
                continue

        new_name = name
        color = value['color']
        description = value.get('description', '')
        modified = False

        # Editing an existing label
        if (
            label.lower() == old_name.lower() and
            (label_color.lower() != color.lower() or label_description != description or label != old_name)
        ):
            modified = True
        edit = LabelEdit(old_name, new_name, color, description, modified=modified)
        break

    return edit


def _parse_labels(config):
    """Parse labels."""

    labels = []
    seen = set()
    colors = _parse_colors(config)
    for value in config.get('labels', []):
        try:
            name = value['name']
            _validate_str(name)
            value['color'] = _resolve_color(value['color'], colors)
            if 'renamed' in value:
                _validate_str(value['renamed'])
            if 'description' in value and not isinstance(value['description'], str):
                raise ValueError("Description for '{}' should be of type str".format(name))
            if name.lower() in seen:
                raise ValueError("The name '{}' is already present in the label list".format(name))
            seen.add(name.lower())
            labels.append(value)
        except Exception:
            traceback.print_exc(file=sys.stdout)

    ignores = set()
    for name in config.get('ignores', []):
        try:
            _validate_str(name)
            ignores.add(name.lower())
        except Exception:
            pass

    return labels, ignores


async def sync(event, gh, config):
    """Sync labels."""

    labels, ignores = _parse_labels(config)
    delete = config.get('delete_labels', False)
    updated = set()
    accept = ','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])

    # No labels defined, assume this has not been configured
    if not labels:
        return

    count = 0
    async for label in gh.getiter(event.labels_url, accept=accept):

        count += 1
        if (count % 20) == 0:
            await asyncio.sleep(1)

        edit = _find_label(labels, label['name'], label['color'], label['description'])
        if edit is not None and edit.modified:
            print('    Updating {}: #{} "{}"'.format(edit.new, edit.color, edit.description))
            await gh.patch(
                event.labels_url,
                {'name': edit.old},
                data={'new_name': edit.new, 'color': edit.color, 'description': edit.description},
                accept=accept
            )
            updated.add(edit.old)
            updated.add(edit.new)
            await asyncio.sleep(1)
        else:
            if edit is None and delete and label['name'].lower() not in ignores:
                print('    Deleting {}: #{} "{}"'.format(label['name'], label['color'], label['description']))
                await gh.delete(
                    event.labels_url,
                    {'name': label['name']},
                    accept=accept
                )
                await asyncio.sleep(1)
            else:
                print('    Skipping {}: #{} "{}"'.format(label['name'], label['color'], label['description']))
            updated.add(label['name'])

    for value in labels:
        name = value['name']
        color = value['color']
        description = value.get('description', '')

        if name not in updated:
            print('    Creating {}: #{} "{}"'.format(name, color, description))
            await gh.post(
                event.labels_url,
                data={'name': name, 'color': color, 'description': description},
                accept=accept
            )
            await asyncio.sleep(1)


async def pending(event, gh):
    """Set task to pending."""

    await gh.post(
        event.statuses_url,
        {'sha': event.sha},
        data={
            "state": "pending",
            "target_url": "https://github.com/gir-bot/label-bot",
            "description": "Pending",
            "context": "{}/labels/sync".format(os.environ.get("GH_BOT"))
        }
    )


async def run(event, gh, config):
    """Run task."""

    try:
        await sync(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    await gh.post(
        event.statuses_url,
        {'sha': event.sha},
        data={
            "state": "success" if success else "failure",
            "target_url": "https://github.com/gir-bot/label-bot",
            "description": "Task completed" if success else "Failed to complete",
            "context": "{}/labels/sync".format(os.environ.get("GH_BOT"))
        }
    )
