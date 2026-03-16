// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0

// FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/shaders/player_model_no_shadow.frag
#version 330 core

in vec3 v_normal;

uniform vec3 u_sunDir;
uniform vec3 u_color;

out vec4 fragColor;

float fallback_lighting(vec3 normal, float ndl) {
    float up = max(normal.y, 0.0);
    float down = max(-normal.y, 0.0);

    float sky_fill = 0.60 + 0.12 * up - 0.08 * down;
    float sun_fill = 0.20 * ndl;

    return clamp(sky_fill + sun_fill, 0.0, 1.0);
}

void main() {
    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_sunDir);

    float ndl = max(dot(n, l), 0.0);
    float lit = fallback_lighting(n, ndl);

    fragColor = vec4(u_color * lit, 1.0);
}