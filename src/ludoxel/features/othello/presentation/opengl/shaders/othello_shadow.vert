// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0

// FILE: src/ludoxel/features/othello/presentation/opengl/shaders/othello_shadow.vert
#version 330 core

layout(location = 0) in vec3 a_pos;

layout(location = 3) in vec4 i_row0;
layout(location = 4) in vec4 i_row1;
layout(location = 5) in vec4 i_row2;
layout(location = 6) in vec4 i_row3;

uniform mat4 u_lightViewProj;

vec4 mul_row_major(vec4 p) {
    return vec4(dot(i_row0, p), dot(i_row1, p), dot(i_row2, p), dot(i_row3, p));
}

void main() {
    vec4 world_pos = mul_row_major(vec4(a_pos, 1.0));
    gl_Position = u_lightViewProj * world_pos;
}
