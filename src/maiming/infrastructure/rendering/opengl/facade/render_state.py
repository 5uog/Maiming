# FILE: src/maiming/infrastructure/rendering/opengl/facade/render_state.py
from __future__ import annotations
from dataclasses import dataclass, field

from .....core.math.vec3 import Vec3
from .....core.math.view_angles import sun_dir_from_az_el_deg
from .cloud_flow_direction import DEFAULT_CLOUD_FLOW_DIRECTION, normalize_cloud_flow_direction

@dataclass
class RendererRuntimeState:
    debug_shadow: bool = False
    shadow_enabled: bool = True
    world_wireframe: bool = False
    outline_selection_enabled: bool = True

    cloud_wireframe: bool = False
    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337
    cloud_flow_direction: str = DEFAULT_CLOUD_FLOW_DIRECTION

    sun_azimuth_deg: float = 45.0
    sun_elevation_deg: float = 60.0
    sun_dir: Vec3 = field(init=False)

    def __post_init__(self) -> None:
        self.set_sun_angles(float(self.sun_azimuth_deg), float(self.sun_elevation_deg))
        self.set_cloud_density(int(self.cloud_density))
        self.set_cloud_seed(int(self.cloud_seed))
        self.set_cloud_flow_direction(str(self.cloud_flow_direction))

    def set_sun_angles(self, azimuth_deg: float, elevation_deg: float) -> None:
        az = float(azimuth_deg) % 360.0
        if az < 0.0:
            az += 360.0

        el = max(0.0, min(90.0, float(elevation_deg)))

        self.sun_azimuth_deg = float(az)
        self.sun_elevation_deg = float(el)
        self.sun_dir = sun_dir_from_az_el_deg(float(self.sun_azimuth_deg), float(self.sun_elevation_deg))

    def set_cloud_density(self, density: int) -> None:
        self.cloud_density = int(max(0, int(density)))

    def set_cloud_seed(self, seed: int) -> None:
        self.cloud_seed = int(seed)

    def set_cloud_flow_direction(self, direction: str) -> None:
        self.cloud_flow_direction = normalize_cloud_flow_direction(str(direction))