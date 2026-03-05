// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/cloud_box.vert
#version 330 core

layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec3 a_normal;

layout(location = 3) in vec3 i_offset; // box center (pattern space)
layout(location = 4) in vec4 i_data;   // x,y,z = scale (box size), w = alphaMul

uniform mat4 u_viewProj;
uniform vec3 u_shift; // smooth translation (world space)

out vec3 v_normal;
out float v_alphaMul;

void main() {
    vec3 scale = i_data.xyz;
    vec3 worldPos = (a_pos * scale) + i_offset + u_shift;
    gl_Position = u_viewProj * vec4(worldPos, 1.0);

    v_normal = a_normal;
    v_alphaMul = i_data.w;
}