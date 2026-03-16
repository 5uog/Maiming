// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0

// FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/shaders/world_no_shadow.frag
#version 330 core

in vec3 v_normal;
in vec2 v_uv;
in vec4 v_uvRect;
in float v_shade;
in float v_sel;

uniform sampler2D u_atlas;
uniform vec3 u_sunDir;

uniform int   u_selMode;
uniform float u_selTint;

out vec4 fragColor;

float fallback_lighting(vec3 normal, float ndl, float shade) {
    float up = max(normal.y, 0.0);
    float down = max(-normal.y, 0.0);

    float sky_fill = 0.56 + 0.18 * up - 0.14 * down;
    float sun_fill = 0.26 * ndl;

    return clamp((sky_fill + sun_fill) * shade, 0.0, 1.0);
}

void main() {
    vec2 uv = mix(v_uvRect.xy, v_uvRect.zw, v_uv);
    vec4 tex = texture(u_atlas, uv);
    if (tex.a < 0.01) discard;

    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_sunDir);

    float ndl = max(dot(n, l), 0.0);
    float shade = clamp(v_shade, 0.0, 1.0);
    float lit = fallback_lighting(n, ndl, shade);

    vec3 base = tex.rgb;
    if (u_selMode == 2 && v_sel > 0.5) {
        float t = clamp(u_selTint, 0.0, 1.0);
        base = mix(base, vec3(1.0), t);
    }

    fragColor = vec4(base * lit, tex.a);
}