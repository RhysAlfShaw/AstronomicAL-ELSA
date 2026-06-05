from __future__ import annotations
import importlib
import sys
import types
from pathlib import Path


from astronomicAL.platform.plugins import PluginManifest

PLUGIN_ID = "astro.druid"
_SPLIT_PACKAGE = "astronomicAL.plugins.druid"

manifest = PluginManifest(
    id=PLUGIN_ID,
    name="DRUID",
    version="0.0.0",
    description=(
        "An Astronomical Source Finder for Optical and Radio images"
        "Load DRUID Contours on Active cutouts."
    ),
    requires=["DRUID"],
    capabilities=["panel", "datasets", "selection", "jobs"],
    tags=[
        "astronomy",
        "euclid",
        "cutout",
        "image",
        "source finding",
        "radio",
        "optical",
        "contours",
        "persistent homology",
    ],
)


def _ensure_split_package() -> None:
    """Allow this plugin to work when loaded as a local plugin file.

    The PluginManager can import ``plugin.py`` under a synthetic module name.
    In that mode normal relative imports fail, so mirror the pattern used by the
    bundled visualisation plugin and ensure the real package path exists in
    ``sys.modules`` before importing implementation modules.
    """

    package_path = Path(__file__).resolve().parent
    existing = sys.modules.get(_SPLIT_PACKAGE)
    if existing is not None:
        existing_path = getattr(existing, "__path__", None)
        if existing_path is None:
            existing.__path__ = [str(package_path)]
        elif str(package_path) not in list(existing_path):
            try:
                existing.__path__.append(str(package_path))
            except Exception:
                existing.__path__ = [str(package_path)]
        return

    package = types.ModuleType(_SPLIT_PACKAGE)
    package.__file__ = str(package_path / "__init__.py")
    package.__path__ = [str(package_path)]
    package.__package__ = _SPLIT_PACKAGE
    sys.modules[_SPLIT_PACKAGE] = package


def _impl(module_name: str):
    _ensure_split_package()
    return importlib.import_module(f"{_SPLIT_PACKAGE}.{module_name}")


def register(api):
    panel_mod = _impl("panel")
    api.register_panel(
        id="DRUID",
        title="DRUID",
        icon="image",
        factory=panel_mod.create_druid_panel,
        description="DRUID panel.",
        category="Image Analysis",
    )
