// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0

// FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/shaders/shadow.vert
#version 330 core

layout(location = 2) in vec2 a_uv;

layout(location = 3) in vec3 i_mn;
layout(location = 4) in vec3 i_mx;

uniform mat4 u_lightViewProj;
uniform int  u_face;

#include "common/face_instance.glsl"

void main() {
    vec2 uv = a_uv;
    vec3 mn = i_mn;
    vec3 mx = i_mx;

    vec3 worldPos = face_world_pos(int(u_face), uv, mn, mx);
    gl_Position = u_lightViewProj * vec4(worldPos, 1.0);
}
