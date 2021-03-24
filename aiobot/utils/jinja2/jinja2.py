import jinja2
from typing import (
    Any, Optional, Mapping
)


class JinjaRender:
    def __init__(self):
        self.env = None

    def render_template(self,
                        template_name: str,
                        context: Optional[Mapping[str, Any]]):
        template = self.env.get_template(template_name)
        return template.render(context)

    def setup(self,
              *args: Any,
              filters=None,
              **kwargs: Any) -> jinja2.Environment:

        kwargs.setdefault("autoescape", True)
        env = jinja2.Environment(*args, **kwargs)

        if filters is not None:
            env.filters.update(filters)
        self.env = env


jinja_render = JinjaRender()
