// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/cloud_box.frag
#version 330 core

in vec3 v_normal;
in float v_alphaMul;

uniform vec3  u_color;
uniform float u_alpha;
uniform vec3  u_sunDir;

out vec4 fragColor;

void main() {
    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_sunDir);

    float ndl = max(dot(n, l), 0.0);

    float ambient = 0.90;
    float lit = ambient + ndl * (1.0 - ambient) * 0.35;

    float a = clamp(u_alpha * v_alphaMul, 0.0, 1.0);
    fragColor = vec4(u_color * lit, a);
}