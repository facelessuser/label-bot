"""Label syncing."""
import asyncio
from collections import namedtuple
import re
import traceback
import sys
from . import util

RE_VALID_COLOR = re.compile('#[a-fA-F0-9]{6}')


class LabelEdit(namedtuple('LabelEdit', ['old', 'new', 'color', 'description', 'modified'])):
    """Label Edit tuple."""


def _validate_str(name):
    """Validate name."""

    if not isinstance(name, str):
        raise TypeError(f"Key value is not of type 'str', type '{type(name)}' received instead")


def _validate_color(color):
    """Validate color."""

    _validate_str(color)

    if RE_VALID_COLOR.match(color) is None:
        raise ValueError(f'{color} is not a valid color')


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
                raise ValueError(f"The name '{name}' is already present in the color list")
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
                raise ValueError(f"Description for '{name}' should be of type str")
            if name.lower() in seen:
                raise ValueError(f"The name '{name}' is already present in the label list")
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

    # No labels defined, assume this has not been configured
    if not labels:
        return

    # Get all labels before we start modifying labels.
    repo_labels = [label async for label in event.get_repo_labels(gh)]

    # Iterate labels deleting or updating labels that need it.
    for label in repo_labels:
        edit = _find_label(labels, label['name'], label['color'], label['description'])
        if edit is not None and edit.modified:
            print(f'    Updating {edit.new}: #{edit.color} "{edit.description}"')
            await event.update_repo_label(gh, edit.old, edit.new, edit.color, edit.description)
            updated.add(edit.old.lower())
            updated.add(edit.new.lower())
            await asyncio.sleep(1)
        else:
            if edit is None and delete and label['name'].lower() not in ignores:
                print(f'    Deleting {label["name"]}: #{label["color"]} "{label["description"]}"')
                await event.remove_repo_label(gh, label['name'])
                await asyncio.sleep(1)
            else:
                print(f'    Skipping {label["name"]}: #{label["color"]} "{label["description"]}"')
            updated.add(label['name'].lower())

    # Create any labels that need creation.
    for value in labels:
        name = value['name']
        color = value['color']
        description = value.get('description', '')

        if name.lower() not in updated:
            print(f'    Creating {name}: #{color} "{description}"')
            await event.add_repo_label(gh, name, color, description)
            await asyncio.sleep(1)


async def pending(event, gh):
    """Set task to pending."""

    await event.set_status(gh, util.EVT_PENDING, 'labels/sync', 'Pending')


async def run(event, gh, config, **kwargs):
    """Run task."""

    try:
        if config.get('error', ''):
            raise Exception(config['error'])
        await sync(event, gh, config)
        success = True
    except Exception:
        traceback.print_exc(file=sys.stdout)
        success = False

    await event.set_status(
        gh,
        util.EVT_SUCCESS if success else util.EVT_FAILURE,
        'labels/sync',
        "Task completed" if success else "Failed to complete task"
    )
