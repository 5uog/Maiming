# FILE: src/maiming/infrastructure/rendering/opengl/facade/gl_renderer_params.py
from __future__ import annotations

from dataclasses import dataclass, field

from maiming.core.math.vec3 import Vec3

@dataclass(frozen=True)
class CameraParams:
    # z_near must be small enough for close-range voxel edges, but too small destroys depth precision.
    # 0.05 is a pragmatic compromise for a 24-bit depth buffer in an indoor-to-midrange scene scale.
    z_near: float = 0.05

    # z_far must cover typical engagement distances and sky objects without pushing precision too low.
    # 200.0 keeps far-plane reasonably bounded while covering the test map and cloud range.
    z_far: float = 200.0

@dataclass(frozen=True)
class ShadowParams:
    enabled: bool = True
    stabilize: bool = True

    # 2048 is a common midpoint: it is high enough to avoid block-sized stair-stepping at normal radii,
    # yet low enough to be feasible in VRAM and bandwidth across a wide GPU range.
    size: int = 2048

    # dark_mul controls minimum brightness in fully shadowed regions.
    # 0.20 preserves readability in a stylized scene and avoids crushing texture detail to black.
    dark_mul: float = 0.20

    # Face culling affects acne vs detachment; exposed because it depends on geometry and bias policy.
    cull_front: bool = False

    # Bias values are expressed in light-space depth units after projection.
    # The defaults are intentionally small; large bias reduces acne but causes visible detachment.
    bias_min: float = 0.00005
    bias_slope: float = 0.00050

    # Polygon offset is applied during shadow rasterization.
    # The factor/units defaults are moderate; they are tuned to reduce acne on unit cubes without
    # producing a "floating shadow" silhouette around contact edges.
    poly_offset_factor: float = 0.50
    poly_offset_units: float = 0.75

@dataclass(frozen=True)
class SunParams:
    # The default angles are chosen to produce strong directional cues and visible shadow silhouettes.
    # Elevation 60° keeps shadows present but not excessively long, which helps readability in an MVP.
    azimuth_deg: float = 45.0
    elevation_deg: float = 60.0

    # distance is the billboard distance for the sun quad.
    # 150.0 places it well beyond the typical play space while remaining inside the far plane by default.
    distance: float = 150.0

    # half_angle_deg controls apparent sun size; a few degrees yields a stylized "Minecraft-like" sun.
    half_angle_deg: float = 2.6

    # light_distance offsets the directional-light "camera" from the center.
    # A moderate value reduces numerical issues in look-at construction while keeping the frustum centered.
    light_distance: float = 60.0

    # ortho_radius controls shadow coverage area around the camera center.
    # 30.0 is chosen to cover the immediate arena with acceptable texel density at 2048.
    ortho_radius: float = 30.0
    ortho_near: float = 0.1
    ortho_far: float = 140.0

@dataclass(frozen=True)
class CloudParams:
    # y is the nominal cloud altitude in world units; 28 keeps clouds above typical arena geometry.
    y: int = 28

    # thickness controls perceived volume; 3 blocks gives depth cues without excessive overdraw.
    thickness: int = 3

    # macro is the cache cell size in world units. 32 matches a chunk-like scale and reduces rebuild rate.
    macro: int = 32

    # rects_per_cell bounds density, keeping the pass lightweight.
    rects_per_cell: int = 1
    candidates_per_cell: int = 5

    # view_radius is aligned with camera z_far scale so clouds exist where the camera can see them.
    view_radius: int = 150

    # speeds are chosen to keep motion subtle and avoid strong parallax that can distract from gameplay.
    speed_x: float = 0.70
    speed_z: float = 0.10

    color: Vec3 = Vec3(1.0, 1.0, 1.0)

    # alpha is high because the shader includes a large ambient term; the visual result remains soft.
    alpha: float = 0.90

    seed: int = 1337

    # Three lanes are used to break coplanar blending without requiring complex sorting.
    lane_offsets: tuple[int, int, int] = (-1, 0, 1)

    # Drop and overlap thresholds are heuristics tuned to keep the instance count bounded and prevent tiling.
    candidate_drop_threshold: float = 0.20
    overlap_thresh: float = 0.35

    # rect_margin pushes boxes away from cell borders to reduce seam artifacts.
    rect_margin: int = 5
    rect_size_min: int = 7
    rect_size_range: int = 8

    # alpha jitter is intentionally narrow to preserve coherence.
    alpha_min: float = 0.88
    alpha_range: float = 0.12

@dataclass(frozen=True)
class SkyParams:
    # clear_color is a stylized daytime sky.
    # Values are chosen to read well under simple sun diffuse without HDR tone mapping.
    clear_color: Vec3 = Vec3(0.55, 0.72, 0.98)

@dataclass(frozen=True)
class GLRendererParams:
    # Grouping parameters clarifies which subsystem each value influences.
    camera: CameraParams = field(default_factory=CameraParams)
    shadow: ShadowParams = field(default_factory=ShadowParams)
    sun: SunParams = field(default_factory=SunParams)
    clouds: CloudParams = field(default_factory=CloudParams)
    sky: SkyParams = field(default_factory=SkyParams)

def default_gl_renderer_params() -> GLRendererParams:
    return GLRendererParams()