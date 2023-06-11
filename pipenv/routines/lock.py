from pipenv.utils.dependencies import (
    get_pipfile_category_using_lockfile_section,
)
from pipenv.vendor import click


def do_lock(
    project,
    system=False,
    clear=False,
    pre=False,
    write=True,
    pypi_mirror=None,
    categories=None,
):
    """Executes the freeze functionality."""
    if not pre:
        pre = project.settings.get("allow_prereleases")
    # Cleanup lockfile.
    if not categories:
        lockfile_categories = project.get_package_categories(for_lockfile=True)
    else:
        lockfile_categories = categories.copy()
        if "dev-packages" in categories:
            lockfile_categories.remove("dev-packages")
            lockfile_categories.insert(0, "develop")
        if "packages" in categories:
            lockfile_categories.remove("packages")
            lockfile_categories.insert(0, "default")
    # Create the lockfile.
    lockfile = project._lockfile(categories=lockfile_categories)
    for category in lockfile_categories:
        for k, v in lockfile.get(category, {}).copy().items():
            if not hasattr(v, "keys"):
                del lockfile[category][k]

    # Resolve package to generate constraints before resolving other categories
    for category in lockfile_categories:
        pipfile_category = get_pipfile_category_using_lockfile_section(category)
        if project.pipfile_exists:
            packages = project.parsed_pipfile.get(pipfile_category, {})
        else:
            packages = project.get_pipfile_section(pipfile_category)

        if write:
            # Alert the user of progress.
            click.echo(
                "{} {} {}".format(
                    click.style("Locking"),
                    click.style("[{}]".format(pipfile_category), fg="yellow"),
                    click.style("dependencies..."),
                ),
                err=True,
            )

        # Prune old lockfile category as new one will be created.
        try:
            del lockfile[category]
        except KeyError:
            pass

        from pipenv.utils.resolver import venv_resolve_deps

        # Mutates the lockfile
        venv_resolve_deps(
            packages,
            which=project._which,
            project=project,
            category=pipfile_category,
            clear=clear,
            pre=pre,
            allow_global=system,
            pypi_mirror=pypi_mirror,
            pipfile=packages,
            lockfile=lockfile,
        )

    # Overwrite any category packages with default packages.
    for category in lockfile_categories:
        if category == "default":
            pass
        if lockfile.get(category):
            lockfile[category].update(
                overwrite_with_default(lockfile.get("default", {}), lockfile[category])
            )
    if write:
        lockfile.update({"_meta": project.get_lockfile_meta()})
        project.write_lockfile(lockfile)
        click.echo(
            "{}".format(
                click.style(
                    "Updated Pipfile.lock ({})!".format(project.get_lockfile_hash()),
                    bold=True,
                )
            ),
            err=True,
        )
    else:
        return lockfile


def overwrite_with_default(default, dev):
    dev_keys = set(list(dev.keys()))
    prod_keys = set(list(default.keys()))
    for pkg in dev_keys & prod_keys:
        dev[pkg] = default[pkg]
    return dev
