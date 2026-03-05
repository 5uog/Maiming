// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/world.vert
#version 330 core

layout(location = 0) in vec3 a_pos;
layout(location = 1) in vec3 a_normal;
layout(location = 2) in vec2 a_uv;

layout(location = 3) in vec3 i_mn;
layout(location = 4) in vec3 i_mx;
layout(location = 5) in vec4 i_uvRect;
layout(location = 6) in float i_shade;
layout(location = 7) in float i_uvRot;

uniform mat4 u_viewProj;
uniform mat4 u_lightViewProj;
uniform int  u_face;

uniform int   u_selMode;
uniform ivec3 u_selBlock;

out vec3 v_normal;
out vec2 v_uv;
out vec4 v_uvRect;
out vec4 v_lightPos;
out float v_shade;
out float v_sel;

vec2 rot_uv(vec2 uv, float r) {
    int k = int(floor(r + 0.5)) & 3;
    if (k == 0) return uv;
    if (k == 1) return vec2(uv.y, 1.0 - uv.x);
    if (k == 2) return vec2(1.0 - uv.x, 1.0 - uv.y);
    return vec2(1.0 - uv.y, uv.x);
}

void main() {
    vec2 uv = a_uv;
    vec3 mn = i_mn;
    vec3 mx = i_mx;

    vec3 worldPos;

    if (u_face == 0) {
        worldPos = vec3(mx.x, mix(mn.y, mx.y, uv.y), mix(mn.z, mx.z, uv.x));
    } else if (u_face == 1) {
        worldPos = vec3(mn.x, mix(mn.y, mx.y, uv.y), mix(mx.z, mn.z, uv.x));
    } else if (u_face == 2) {
        worldPos = vec3(mix(mn.x, mx.x, uv.x), mx.y, mix(mn.z, mx.z, uv.y));
    } else if (u_face == 3) {
        worldPos = vec3(mix(mn.x, mx.x, uv.x), mn.y, mix(mx.z, mn.z, uv.y));
    } else if (u_face == 4) {
        worldPos = vec3(mix(mx.x, mn.x, uv.x), mix(mn.y, mx.y, uv.y), mx.z);
    } else {
        worldPos = vec3(mix(mn.x, mx.x, uv.x), mix(mn.y, mx.y, uv.y), mn.z);
    }

    gl_Position = u_viewProj * vec4(worldPos, 1.0);

    v_normal = a_normal;
    v_uv = rot_uv(uv, i_uvRot);
    v_uvRect = i_uvRect;
    v_lightPos = u_lightViewProj * vec4(worldPos, 1.0);
    v_shade = i_shade;

    ivec3 b = ivec3(floor(i_mn + vec3(1e-6)));
    v_sel = (u_selMode != 0 && all(equal(b, u_selBlock))) ? 1.0 : 0.0;
}