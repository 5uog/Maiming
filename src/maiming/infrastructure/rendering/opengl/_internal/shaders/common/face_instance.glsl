// FILE: src/maiming/infrastructure/rendering/opengl/_internal/shaders/common/face_instance.glsl
vec3 face_world_pos(int faceIdx, vec2 uv, vec3 mn, vec3 mx) {
    if (faceIdx == 0) { return vec3(mx.x, mix(mn.y, mx.y, uv.y), mix(mn.z, mx.z, uv.x)); }
    if (faceIdx == 1) { return vec3(mn.x, mix(mn.y, mx.y, uv.y), mix(mx.z, mn.z, uv.x)); }
    if (faceIdx == 2) { return vec3(mix(mn.x, mx.x, uv.x), mx.y, mix(mn.z, mx.z, uv.y)); }
    if (faceIdx == 3) { return vec3(mix(mn.x, mx.x, uv.x), mn.y, mix(mx.z, mn.z, uv.y)); }
    if (faceIdx == 4) { return vec3(mix(mx.x, mn.x, uv.x), mix(mn.y, mx.y, uv.y), mx.z); }
    return vec3(mix(mn.x, mx.x, uv.x), mix(mn.y, mx.y, uv.y), mn.z);
}