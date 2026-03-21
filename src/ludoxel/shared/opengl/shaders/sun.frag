// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0
#version 330 core
in vec2 v_uv;
out vec4 fragColor;
void main() {
    float border = 0.08;
    float inX = step(border, v_uv.x) * step(v_uv.x, 1.0 - border);
    float inY = step(border, v_uv.y) * step(v_uv.y, 1.0 - border);
    float inner = inX * inY;
    float core = 1.0;
    float edge = clamp(core - inner, 0.0, 1.0);
    vec3 coreCol = vec3(1.00, 0.96, 0.78);
    vec3 edgeCol = vec3(1.00, 0.88, 0.55);
    float cx = abs(v_uv.x - 0.5) * 2.0;
    float cy = abs(v_uv.y - 0.5) * 2.0;
    float t = max(cx, cy);
    float center = 1.0 - smoothstep(0.0, 1.0, t);
    vec3 col = mix(coreCol, edgeCol, edge * 0.75);
    col += vec3(1.0, 0.9, 0.6) * (center * 0.06);
    fragColor = vec4(col, 1.0);
}