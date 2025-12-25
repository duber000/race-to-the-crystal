#version 330

uniform mat4 projection;
uniform mat4 view;
uniform mat4 model;

in vec3 in_position;

out vec3 v_world_pos;
out float v_distance;

void main() {
    vec4 world_pos = model * vec4(in_position, 1.0);
    vec4 view_pos = view * world_pos;
    gl_Position = projection * view_pos;

    v_world_pos = world_pos.xyz;
    v_distance = length(view_pos.xyz);
}
