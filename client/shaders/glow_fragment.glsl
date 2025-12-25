#version 330

uniform vec4 base_color;
uniform float glow_intensity;

in vec3 v_world_pos;
in float v_distance;

out vec4 fragColor;

void main() {
    // Distance-based fade (closer = brighter)
    float distance_fade = 1.0 / (1.0 + v_distance * 0.01);

    // Core glow calculation
    float glow_factor = glow_intensity * distance_fade;
    vec4 glow_color = base_color * (1.0 + glow_factor);

    // Apply alpha for transparency
    float alpha = base_color.a * distance_fade;

    fragColor = vec4(glow_color.rgb, alpha);
}
