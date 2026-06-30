from __future__ import annotations

from functools import cache
from importlib.resources import files
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined, select_autoescape
from starlette.responses import HTMLResponse


def package_path(package: str, *parts: str) -> str:
    return str(files(package).joinpath(*parts))


@cache
def template_environment(template_dir: str) -> Environment:
    return Environment(
        loader=FileSystemLoader(template_dir),
        autoescape=select_autoescape(("html", "xml"), default_for_string=True),
        undefined=StrictUndefined,
    )


def render_template_from(environment: Environment, template_name: str, **context: Any) -> str:
    return environment.get_template(template_name).render(**context)


def html_response(html: str, *, status_code: int = 200) -> HTMLResponse:
    return HTMLResponse(html, status_code=status_code)
