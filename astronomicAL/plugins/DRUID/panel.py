from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional, Tuple

import numpy as np
import panel as pn
import holoviews as hv

import uuid


import DRUID
from DRUID import sf


def create_druid_panel(
    context: Any,
    data: Any = None,
    state: Optional[Dict[str, Any]] = None,
    **kwargs: Any,
) -> Tuple[pn.viewable.Viewable, DruidPanel]:
    panel = DruidPanel(context=context, data=data, state=state, **kwargs)
    return panel.view(), panel


class DruidPanel:
    """
    A panel to run the DRUID source finder on active cutouts.
    Listens for cutout events, processes the image via JobManager,
    and publishes the resulting source catalog as an artifact.
    """

    def __init__(self, context, data=None, state=None, **kwargs):
        self.context = context
        self.panel_id = f"astro.druid.{uuid.uuid4().hex}"
        self._job_handle = None

        # State tracking
        self._current_cutout_id = None
        self._current_dataset_id = None

        self._build_widgets()
        self._build_layout()
        self._bind_events()

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _build_widgets(self):
        self.status = pn.pane.Markdown(
            "Waiting for an active cutout...", sizing_mode="stretch_width"
        )

        # Standard source extraction parameters
        self.threshold_input = pn.widgets.FloatInput(
            name="Detection Threshold (Sigma)",
            value=3.0,
            step=0.5,
            sizing_mode="stretch_width",
        )

        self.run_button = pn.widgets.Button(
            name="Run DRUID",
            button_type="primary",
            disabled=True,
            sizing_mode="stretch_width",
        )
        self.run_button.on_click(self._run_druid_clicked)

    def _build_layout(self):
        self.layout = pn.Column(
            pn.pane.Markdown("### DRUID Source Finder"),
            self.threshold_input,
            self.run_button,
            self.status,
            sizing_mode="stretch_width",
            margin=(10, 10, 10, 10),
        )

    def panel(self):
        return self.layout

    def dispose(self):
        if self._job_handle:
            try:
                self._job_handle.cancel()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Event Wiring
    # ------------------------------------------------------------------

    def _bind_events(self):
        events = getattr(self.context, "events", None)
        if events:
            # Listen for when the Euclid Cutout panel finishes producing an image
            events.subscribe("astro.cutout.updated", self._on_cutout_updated)
            events.subscribe("selection.focus.cleared", self._on_focus_cleared)

    def _on_cutout_updated(self, topic, payload):
        """Triggered when a new cutout is published to the artifact store."""
        if not isinstance(payload, dict):
            return

        self._current_cutout_id = payload.get("artifact_id")
        self._current_dataset_id = payload.get("dataset_id")

        if self._current_cutout_id:
            self.status.object = f"**Cutout detected.** Ready to run DRUID."
            self.run_button.disabled = False

    def _on_focus_cleared(self, topic, payload):
        """Reset the panel if the user clears their current selection."""
        self._current_cutout_id = None
        self.status.object = "Waiting for an active cutout..."
        self.run_button.disabled = True

    # ------------------------------------------------------------------
    # Job Execution & Publishing
    # ------------------------------------------------------------------

    def _run_druid_clicked(self, event):
        if not self._current_cutout_id:
            return

        self.status.object = "Running DRUID in the background..."
        self.run_button.disabled = True

        jobs = getattr(self.context, "jobs", None)
        if jobs:
            self._job_handle = jobs.submit(
                self._druid_worker,
                cutout_id=self._current_cutout_id,
                threshold=self.threshold_input.value,
                title="DRUID Source Detection",
                on_done=self._on_druid_done,
                on_error=self._on_error,
            )
        else:
            self.status.object = "Error: JobManager is not available."

    def _druid_worker(self, cutout_id, threshold, cancel_token=None):
        """
        Background worker. Do NOT update UI elements in this function.
        Returns the data payload to be passed to _on_druid_done.
        """
        artifacts = getattr(self.context, "artifacts", None)
        if not artifacts:
            raise RuntimeError("Artifact store is not available.")

        cutout_payload = artifacts.get(cutout_id)
        if not cutout_payload or "image" not in cutout_payload:
            raise ValueError("Could not retrieve image data from the cutout artifact.")

        image_data = cutout_payload.get("image")

        # ---------------------------------------------------------
        # TODO: Insert actual DRUID processing logic here.
        # For example: sources = druid.detect(image_data, threshold)
        # ---------------------------------------------------------
        img_center = (image_data.shape[1] // 2, image_data.shape[0] // 2)
        img_size = (image_data.shape[1], image_data.shape[0])
        # Mock countours. just a circle in the center of the image for demonstration.
        # circle contours
        radius = min(img_size) // 4
        theta = np.linspace(0, 2 * np.pi, 100)
        x = img_center[0] + radius * np.cos(theta)
        y = img_center[1] + radius * np.sin(theta)
        contours = []
        for i in range(len(x)):
            contours.append((x[i], y[i]))

        return {
            "dataset_id": self._current_dataset_id,
            "contours": contours,  # Replace with actual DRUID contours
            "threshold_used": threshold,
            "source_cutout_id": cutout_id,
        }

    def _on_druid_done(self, result):
        """Called on the main thread when the background job finishes."""
        self.run_button.disabled = False
        source_count = len(result["catalog"]["x"])
        self.status.object = f"**DRUID finished!** Found {source_count} sources."

        # Publish the results to the ArtifactStore so other plugins can use it
        artifacts = getattr(self.context, "artifacts", None)
        events = getattr(self.context, "events", None)

        if artifacts:
            # Store the extracted catalog
            artifact_id = artifacts.put(
                type="astro.druid.catalog",
                payload=result,
                dataset_id=result.get("dataset_id"),
                persist=False,
            )

            if events and artifact_id:
                # Announce to the app that DRUID results are available
                events.publish(
                    "astro.druid.completed",
                    {
                        "artifact_id": artifact_id,
                        "dataset_id": result.get("dataset_id"),
                        "source_count": source_count,
                    },
                )

    def _on_error(self, exc):
        self.run_button.disabled = False
        self.status.object = f"**Error running DRUID:** `{exc}`"

    def view(self) -> pn.viewable.Viewable:
        # You can add any initial load scheduling here if needed later
        return self.layout

    def panel(self) -> pn.viewable.Viewable:
        return self.view()
