"""Wildcard labels."""
from wcmatch import glob
from gidgethub import sansio
import traceback
import sys
import os


def get_flags(config):
    """Get glob flags."""

    flags = glob.GLOBSTAR | glob.DOTGLOB | glob.NEGATE | glob.SPLIT | glob.NEGATEALL
    if config.get('brace_expansion', False):
        flags |= glob.BRACE
    if config.get('extended_glob', False):
        flags |= glob.EXTGLOB | glob.MINUSNEGATE
    if config.get('case_insensitive', False):
        flags |= glob.IGNORECASE
    return flags


def get_labels(rules, files, flags):
    """Sync labels."""

    add_labels = {}
    for file in files:
        for label in rules:
            try:
                names = label['labels']
                lows = [n.lower() for n in names]
            except Exception:
                traceback.print_exc(file=sys.stdout)
                continue

            match = False
            for pattern in label['patterns']:
                try:
                    match = glob.globmatch(file, pattern, flags=flags)
                except Exception:
                    traceback.print_exc(file=sys.stdout)
                    match = False
                if match:
                    break
            if match:
                for index, low in enumerate(lows):
                    if low not in add_labels:
                        add_labels[low] = names[index]

    remove_labels = {}
    for label in rules:
        try:
            names = label['labels']
            lows = [n.lower() for n in names]
        except Exception:
            traceback.print_exc(file=sys.stdout)
            continue

        for index, low in enumerate(lows):
            if low not in add_labels and low not in remove_labels:
                remove_labels[low] = names[index]

    return add_labels, remove_labels


async def wildcard_labels(event, gh, config):
    """Label issues by files that have changed."""

    rules = config.get('rules', [])
    if rules:
        flags = get_flags(config)
        files = await get_changed_files(event, gh)
        add, remove = get_labels(rules, files, flags)
        await update_issue_labels(event, gh, add, remove, config.get('quick_labels', True))


async def get_changed_files(event, gh):
    """Get changed files."""

    files = []
    compare = await gh.getitem(
        event.compare_url,
        {'base': event.base, 'head': event.head}
    )
    for file in compare['files']:
        files.append(file['filename'])
    return files


async def update_issue_labels(event, gh, add_labels, remove_labels, quick):
    """Update issue labels."""

    labels = []
    changed = False

    print('----- wild quick', str(quick))

    if quick:
        current_labels = event.labels
    else:
        current_labels = [x async for x in event.live_labels(gh)]

    print('----- wild labels')
    print(current_labels)
    print(event.labels)

    for name in current_labels:
        low = name.lower()
        if low not in remove_labels:
            labels.append(name)
            if low in add_labels:
                del add_labels[low]
        else:
            changed = True

    new_labels = [label for label in add_labels.values()]
    if new_labels:
        changed = True
        labels.extend(new_labels)
    if changed:
        event.labels.clear()
        event.labels.extend(labels)
        await gh.put(
            event.issue_labels_url,
            {'number': event.number},
            data={'labels': labels},
            accept=','.join([sansio.accept_format(), 'application/vnd.github.symmetra-preview+json'])
        )


async def pending(event, gh):
    """Set task to pending."""

    await gh.post(
        event.statuses_url,
        {'sha': event.sha},
        data={
            "state": "pending",
            "target_url": "https://github.com/gir-bot/label-bot",
            "description": "Pending",
            "context": "{}/labels/auto-labels".format(os.environ.get("GH_BOT"))
        }
    )


async def run(event, gh, config):
    """Run task."""

    try:
        await wildcard_labels(event, gh, config)
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
            "context": "{}/labels/auto-labels".format(os.environ.get("GH_BOT"))
        }
    )
