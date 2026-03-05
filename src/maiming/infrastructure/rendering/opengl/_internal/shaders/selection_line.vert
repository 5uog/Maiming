// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/selection_line.vert
#version 330 core

layout(location = 0) in vec3 a_pos;

uniform mat4 u_viewProj;

void main() {
    gl_Position = u_viewProj * vec4(a_pos, 1.0);
}