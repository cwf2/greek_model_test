# Experiments

One script per topic, named to match its paired report: `<topic>.py` here
reproduces the data that `../reports/<topic>.md` narrates. These are meant to
be run, not read as documentation — leave dead ends and one-off exploration
out, they belong in the shell/Python session that found the result, not here.

Scripts that depend on external data (e.g. cloning a UD treebank repo from
GitHub) should pin a specific commit/tag rather than tracking a branch HEAD,
so re-running the script later reproduces the same finding rather than
whatever that upstream repo looks like by then.

See [README.md](../README.md#reports) for the full write-up-a-finding
workflow.
