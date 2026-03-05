// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/world.frag
#version 330 core

in vec3 v_normal;
in vec2 v_uv;
in vec4 v_uvRect;
in vec4 v_lightPos;
in float v_shade;
in float v_sel;

uniform sampler2D u_atlas;

// Depth-compare shadow map.
uniform sampler2DShadow u_shadowMap;
uniform int   u_shadowEnabled;
uniform vec2  u_shadowTexel;     // 1.0 / shadow_size
uniform float u_shadowDarkMul;   // 0..1
uniform float u_shadowBiasMin;
uniform float u_shadowBiasSlope;

uniform vec3 u_sunDir;
uniform int u_debugShadow;

uniform int   u_selMode;   // 0 none, 1 outline, 2 tint
uniform float u_selTint;   // 0..1

out vec4 fragColor;

float shadow_factor(float ndl) {
    if (u_shadowEnabled == 0) {
        return (u_debugShadow != 0) ? 0.0 : 1.0;
    }

    vec3 ndc = v_lightPos.xyz / max(v_lightPos.w, 1e-6);
    vec3 uvz = ndc * 0.5 + 0.5;

    if (uvz.x < 0.0 || uvz.x > 1.0 || uvz.y < 0.0 || uvz.y > 1.0) return 1.0;
    if (uvz.z < 0.0 || uvz.z > 1.0) return 1.0;

    float bias = max(u_shadowBiasMin, u_shadowBiasSlope * (1.0 - ndl));

    float tex = max(u_shadowTexel.x, u_shadowTexel.y);
    bias += 0.25 * tex;

    float lit = texture(u_shadowMap, vec3(uvz.xy, uvz.z - bias));

    return mix(u_shadowDarkMul, 1.0, lit);
}

void main() {
    vec2 uv = mix(v_uvRect.xy, v_uvRect.zw, v_uv);
    vec4 tex = texture(u_atlas, uv);
    if (tex.a < 0.01) discard;

    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_sunDir);

    float ndl = max(dot(n, l), 0.0);

    float sh = (ndl > 1e-6) ? shadow_factor(ndl) : 1.0;

    if (u_debugShadow != 0) {
        fragColor = vec4(sh, sh, sh, 1.0);
        return;
    }

    float shade = clamp(v_shade, 0.0, 1.0);

    float ambient = 0.20;
    float amb_term = ambient * shade;
    float dir_term = (ndl * (1.0 - ambient)) * shade;

    float lit = amb_term + dir_term * sh;

    vec3 base = tex.rgb;
    if (u_selMode == 2 && v_sel > 0.5) {
        float t = clamp(u_selTint, 0.0, 1.0);
        base = mix(base, vec3(1.0), t);
    }

    fragColor = vec4(base * lit, tex.a);
}