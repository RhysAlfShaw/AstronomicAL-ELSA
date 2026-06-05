from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import panel as pn
import holoviews as hv


def create_druid_panel(
    context: Any,
    data: Any = None,
    state: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Tuple[pn.viewable.Viewable, DruidPanel]:
    panel = DruidPanel(context=context, data=data, state=state, **kwargs)
    return panel.view(), panel


class DruidPanel:
    def __init__(
        self,
        context: Any,
        data: Any = None,
        state: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ):
        self.context = context
        self.data = data
        self.state = state or {}
        self.kwargs = kwargs
        # Initialize your panel here, e.g., create widgets, set up layout, etc.

    def view(self) -> pn.viewable.Viewable:
        # Return the Panel view for this plugin
        return pn.Column(pn.pane.Markdown("DRUID Panel Content"))
