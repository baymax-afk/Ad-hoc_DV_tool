from __future__ import annotations

import plotly.graph_objects as go


def export_png(fig: go.Figure, width: int = 1200, height: int = 700) -> bytes:
    try:
        return fig.to_image(format="png", width=width, height=height, scale=2)
    except Exception as exc:
        raise RuntimeError(
            f"PNG export failed. Ensure kaleido is installed: pip install kaleido. Error: {exc}"
        ) from exc


def export_svg(fig: go.Figure, width: int = 1200, height: int = 700) -> bytes:
    try:
        return fig.to_image(format="svg", width=width, height=height)
    except Exception as exc:
        raise RuntimeError(f"SVG export failed: {exc}") from exc
