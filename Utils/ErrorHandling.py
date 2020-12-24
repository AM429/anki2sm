import click


def ep(p) -> None:
	"""error print"""
	click.secho(str(">> " + p), fg="red", nl=False)


def pp(p) -> None:
	"""pretty print"""
	click.secho(">> ", fg="green", nl=False)
	click.echo(p)


def wp(p) -> None:
	"""warning print - yellow in color"""
	click.secho(p, fg="yellow", nl=True)