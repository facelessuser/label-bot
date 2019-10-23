"""Label management."""
from collections import namedtuple


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
        _validate_color(color)
        _validate_str(name)
        if name in colors:
            raise ValueError("The name '{}' is already present in the color list".format(name))
        colors[name] = color[1:]
    return colors


def find_label(labels, label, label_color, label_description):
    """Find label."""

    edit = None
    for value in labels:
        name = value['name']
        old_name = value.get('renamed', name)

        if label.lower() != old_name.lower():
            continue

        new_name = name
        color = value['color']
        description = value.get('description', '')
        modified = False

        # Editing an existing label
        if (
            label.lower() == old_name.lower() and
            (label_color.lower() != color.lower() or label_description != description)
        ):
            modified = True
        edit = LabelEdit(old_name, new_name, color, description, modified=modified)
        break

    return edit


def parse_labels(config):
    """Parse labels."""

    labels = []
    seen = set()
    colors = parse_colors(config)
    for value in config.get('labels', {}):
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

    ignores = set()
    for name in config.get('ignores', []):
        _validate_str(name)
        ignores.add(name.lower())

    return labels, ignores


async def manage(event, gh, config):
    """Sync labels."""

    labels, ignores = parse_labels
    delete = config.get('delete_labels', False)
    updated = set()
    label_url = event.data['repository']['labels_url']
    accept = 'application/vnd.github.symmetra-preview+json'

    async for label in gh.getiter(label_url.replace('{/name}', ''), accept=accept):
        edit = find_label(labels, label['name'], label['color'], label['description'])
        if edit is not None and edit.modified:
            print('    Updating {}: #{} "{}"'.format(edit.new, edit.color, edit.description))
            await gh.patch(
                label_url,
                {'name': edit.old_name},
                data={'new_name': edit.new_name, 'color': edit.color, 'description': edit.description},
                accept=accept
            )
            updated.add(edit.old)
            updated.add(edit.new)
        else:
            if edit is None and delete and label['name'].lower() not in ignores:
                print('    Deleting {}: #{} "{}"'.format(label['name'], label['color'], label['description']))
                await gh.delete(
                    label_url,
                    {'name': label['name']},
                    accept=accept
                )
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
                label_url.replace('{/name}', ''),
                data={'new_name': name, 'color': color, 'description': description},
                accept=accept
            )
