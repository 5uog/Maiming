// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0

// FILE: src/ludoxel/infrastructure/rendering/opengl/_internal/shaders/othello.vert
#version 330 core

layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec3 a_color;

layout(location = 3) in vec4 i_row0;
layout(location = 4) in vec4 i_row1;
layout(location = 5) in vec4 i_row2;
layout(location = 6) in vec4 i_row3;
layout(location = 7) in vec4 i_tint;

uniform mat4 u_viewProj;
uniform mat4 u_lightViewProj;

out vec3 v_normal;
out vec3 v_color;
out float v_alpha;
out vec4 v_lightPos;

vec4 mul_row_major(vec4 p) {
    return vec4(dot(i_row0, p), dot(i_row1, p), dot(i_row2, p), dot(i_row3, p));
}

mat3 model_mat3() {
    return mat3(
        i_row0.x, i_row1.x, i_row2.x,
        i_row0.y, i_row1.y, i_row2.y,
        i_row0.z, i_row1.z, i_row2.z
    );
}

void main() {
    vec4 world_pos = mul_row_major(vec4(a_pos, 1.0));
    gl_Position = u_viewProj * world_pos;

    mat3 m = model_mat3();
    v_normal = normalize(transpose(inverse(m)) * a_normal);
    v_color = a_color * i_tint.rgb;
    v_alpha = i_tint.a;
    v_lightPos = u_lightViewProj * world_pos;
}