// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/first_person_face.frag
#version 330 core

in vec3 v_normal;
in vec2 v_uv;
in vec4 v_uvRect;

uniform sampler2D u_texture;
uniform vec3 u_sunDir;

out vec4 fragColor;

float fallback_lighting(vec3 normal, float ndl) {
    float up = max(normal.y, 0.0);
    float down = max(-normal.y, 0.0);
    float skyFill = 0.56 + 0.18 * up - 0.14 * down;
    float sunFill = 0.26 * ndl;
    return clamp(skyFill + sunFill, 0.0, 1.0);
}

void main() {
    vec2 uv = mix(v_uvRect.xy, v_uvRect.zw, v_uv);
    vec4 tex = texture(u_texture, uv);
    if (tex.a < 0.01) { discard; }

    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_sunDir);
    float ndl = max(dot(n, l), 0.0);
    float lit = fallback_lighting(n, ndl);
    fragColor = vec4(tex.rgb * lit, tex.a);
}