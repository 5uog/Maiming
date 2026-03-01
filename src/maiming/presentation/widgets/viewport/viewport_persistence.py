# FILE: src/maiming/presentation/widgets/viewport/viewport_persistence.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from maiming.core.math.vec3 import Vec3
from maiming.application.session.session_manager import SessionManager
from maiming.infrastructure.rendering.opengl.facade.gl_renderer import GLRenderer
from maiming.infrastructure.persistence.app_state_store import (
    AppStateStore,
    PersistedSettings,
    PersistedPlayer,
    PersistedWorld,
    AppState,
)

@dataclass
class PersistedRuntime:
    invert_x: bool = False
    invert_y: bool = False

    cloud_wire: bool = False

    cloud_enabled: bool = True
    cloud_density: int = 1
    cloud_seed: int = 1337

    world_wire: bool = False
    shadow_enabled: bool = True

    build_mode: bool = False
    auto_jump_enabled: bool = False

    sun_az_deg: float = 45.0
    sun_el_deg: float = 60.0

def apply_persisted_state_if_present(
    *,
    project_root: Path,
    session: SessionManager,
    renderer: GLRenderer,
) -> PersistedRuntime:
    store = AppStateStore(project_root=Path(project_root))
    st = store.load()
    if st is None:
        return PersistedRuntime()

    ps = st.settings
    session.settings.set_fov(float(ps.fov_deg))
    session.settings.set_mouse_sens(float(ps.mouse_sens_deg_per_px))

    out = PersistedRuntime(
        invert_x=bool(ps.invert_x),
        invert_y=bool(ps.invert_y),
        world_wire=bool(ps.world_wireframe),
        shadow_enabled=bool(ps.shadow_enabled),
        sun_az_deg=float(ps.sun_az_deg),
        sun_el_deg=float(ps.sun_el_deg),
        cloud_enabled=bool(ps.cloud_enabled),
        cloud_density=int(max(0, min(4, int(ps.cloud_density)))),
        cloud_seed=int(max(0, min(9999, int(ps.cloud_seed)))),
        build_mode=bool(ps.build_mode),
        auto_jump_enabled=bool(ps.auto_jump_enabled),
        cloud_wire=False,
    )

    pp = st.player
    p = session.player
    p.position = Vec3(float(pp.pos_x), float(pp.pos_y), float(pp.pos_z))
    p.velocity = Vec3(float(pp.vel_x), float(pp.vel_y), float(pp.vel_z))
    p.yaw_deg = float(pp.yaw_deg)
    p.pitch_deg = float(pp.pitch_deg)
    p.clamp_pitch()
    p.on_ground = bool(pp.on_ground)
    p.crouch_eye_offset = float(max(0.0, min(float(p.crouch_eye_drop), float(pp.crouch_eye_offset))))
    p.hold_jump_queued = False
    p.auto_jump_pending = False
    p.auto_jump_cooldown_s = 0.0
    p.auto_jump_start_y = float(p.position.y)

    pw = st.world
    if pw.blocks:
        session.world.blocks.clear()
        for (x, y, z), s in pw.blocks.items():
            session.world.blocks[(int(x), int(y), int(z))] = str(s)
        session.world.revision = int(max(1, int(pw.revision)))

    renderer.set_world_wireframe(bool(out.world_wire))
    renderer.set_shadow_enabled(bool(out.shadow_enabled))
    renderer.set_sun_angles(float(out.sun_az_deg), float(out.sun_el_deg))

    renderer.set_cloud_wireframe(bool(out.cloud_wire))
    renderer.set_cloud_enabled(bool(out.cloud_enabled))
    renderer.set_cloud_density(int(out.cloud_density))
    renderer.set_cloud_seed(int(out.cloud_seed))

    return out

def save_state(
    *,
    project_root: Path,
    session: SessionManager,
    renderer: GLRenderer,
    invert_x: bool,
    invert_y: bool,
    cloud_enabled: bool,
    cloud_density: int,
    cloud_seed: int,
    build_mode: bool,
    auto_jump_enabled: bool,
    world_wire: bool,
    shadow_enabled: bool,
    sun_az_deg: float,
    sun_el_deg: float,
) -> None:
    store = AppStateStore(project_root=Path(project_root))

    settings = PersistedSettings(
        fov_deg=float(session.settings.fov_deg),
        mouse_sens_deg_per_px=float(session.settings.mouse_sens_deg_per_px),
        invert_x=bool(invert_x),
        invert_y=bool(invert_y),
        world_wireframe=bool(world_wire),
        shadow_enabled=bool(shadow_enabled),
        sun_az_deg=float(sun_az_deg),
        sun_el_deg=float(sun_el_deg),
        cloud_enabled=bool(cloud_enabled),
        cloud_density=int(cloud_density),
        cloud_seed=int(cloud_seed),
        build_mode=bool(build_mode),
        auto_jump_enabled=bool(auto_jump_enabled),
    )

    pl = session.player
    player = PersistedPlayer(
        pos_x=float(pl.position.x),
        pos_y=float(pl.position.y),
        pos_z=float(pl.position.z),
        vel_x=float(pl.velocity.x),
        vel_y=float(pl.velocity.y),
        vel_z=float(pl.velocity.z),
        yaw_deg=float(pl.yaw_deg),
        pitch_deg=float(pl.pitch_deg),
        on_ground=bool(pl.on_ground),
        jump_cooldown_s=0.0,
        crouch_eye_offset=float(max(0.0, min(float(pl.crouch_eye_drop), float(pl.crouch_eye_offset)))),
    )

    world = PersistedWorld(
        revision=int(session.world.revision),
        blocks={k: str(v) for (k, v) in session.world.blocks.items()},
    )

    state = AppState(version=2, settings=settings, player=player, world=world)
    store.save(state)