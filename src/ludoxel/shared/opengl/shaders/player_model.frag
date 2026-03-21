// Copyright 2026 Kento Konishi (https://github.com/5uog)
// SPDX-License-Identifier: Apache-2.0
#version 330 core
in vec3 v_normal;
in vec4 v_lightPos;
uniform sampler2DShadow u_shadowMap;
uniform int   u_shadowEnabled;
uniform vec2  u_shadowTexel;
uniform float u_shadowDarkMul;
uniform float u_shadowBiasMin;
uniform float u_shadowBiasSlope;
uniform vec3 u_sunDir;
uniform vec3 u_color;
uniform int  u_debugShadow;
out vec4 fragColor;
float shadow_pcf4(vec3 uvz, float bias) {
    vec2 t = u_shadowTexel;
    float z = uvz.z - bias;
    float s0 = texture(u_shadowMap, vec3(uvz.xy + vec2(-0.5, -0.5) * t, z));
    float s1 = texture(u_shadowMap, vec3(uvz.xy + vec2( 0.5, -0.5) * t, z));
    float s2 = texture(u_shadowMap, vec3(uvz.xy + vec2(-0.5,  0.5) * t, z));
    float s3 = texture(u_shadowMap, vec3(uvz.xy + vec2( 0.5,  0.5) * t, z));
    return 0.25 * (s0 + s1 + s2 + s3);
}
float shadow_factor(float ndl) {
    if (u_shadowEnabled == 0) { return (u_debugShadow != 0) ? 0.0 : 1.0; }
    vec3 ndc = v_lightPos.xyz / max(v_lightPos.w, 1e-6);
    vec3 uvz = ndc * 0.5 + 0.5;
    if (uvz.x < 0.0 || uvz.x > 1.0 || uvz.y < 0.0 || uvz.y > 1.0) return 1.0;
    if (uvz.z < 0.0 || uvz.z > 1.0) return 1.0;
    float tex = max(u_shadowTexel.x, u_shadowTexel.y);
    float bias = max(u_shadowBiasMin, u_shadowBiasSlope * (1.0 - ndl));
    bias += 0.35 * tex;
    float lit = shadow_pcf4(uvz, bias);
    return mix(u_shadowDarkMul, 1.0, lit);
}
void main() {
    vec3 n = normalize(v_normal);
    vec3 l = normalize(u_sunDir);
    float ndl = max(dot(n, l), 0.0);
    float sh = (ndl > 1e-6) ? shadow_factor(ndl) : 1.0;
    if (u_debugShadow != 0) {
        fragColor = vec4(sh, sh, sh, 1.0);
        return;
    }
    float ambient = 0.20;
    float lit = ambient + (ndl * (1.0 - ambient)) * sh;
    fragColor = vec4(u_color * lit, 1.0);
}