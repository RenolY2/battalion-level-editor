from OpenGL.GL import *

vertshader = """
#version 330 compatibility
layout(location = 0) in vec4 vert;
layout(location = 2) in vec4 color;
layout(location = 3) in vec2 texCoord1;
layout(location = 4) in vec2 texCoord2;

out vec2 fragTexCoord1;
out vec2 fragTexCoord2;
out vec4 fragColor;

void main(void)
{
    // Pass the tex coord straight through to the fragment shader
    fragTexCoord1 = texCoord1;
    fragTexCoord2 = texCoord2;
    fragColor = color;

   gl_Position = gl_ModelViewProjectionMatrix* vert;
}   
"""

fragshader = """
#version 330
in vec2 fragTexCoord1; //this is the texture coord
in vec2 fragTexCoord2; 
in vec4 fragColor;

out vec4 finalColor; //this is the output color of the pixel
uniform sampler2D tex;
uniform sampler2D tex2;

//uniform vec3 light;// = vec3(0.0, 1.0, 0.0);
//vec4 ambient = vec4(0.1, 0.1, 0.1, 1.0);

void clampvector(in vec4 vector, out vec4 result) {
    result.x = clamp(vector.x, 0.0, 1.0);
    result.y = clamp(vector.y, 0.0, 1.0);
    result.z = clamp(vector.z, 0.0, 1.0);
    result.w = clamp(vector.w, 0.0, 1.0);
}

void main (void)
{
    vec4 texcolor2 = texture(tex2, fragTexCoord2);
    vec4 texcolor = texture(tex, fragTexCoord1);
    float a = fragColor.a * texcolor2.a;
    vec4 color = a*texcolor2 + (1-a)*texcolor;
    finalColor = color*vec4(fragColor.rgb, 1)*3;
}
"""

fragshaderSimple = """
#version 330
in vec2 fragTexCoord; //this is the texture coord
in vec3 vecNormal; // normal vector
in vec3 vecBinormal;
in vec3 vecTangent;
in vec2 bumpTexCoord; // coordinates on bump texture

out vec4 finalColor; //this is the output color of the pixel
uniform sampler2D tex;
uniform sampler2D bump;

uniform vec3 light;// = vec3(0.0, 1.0, 0.0);
vec4 ambient = vec4(0.1, 0.1, 0.1, 1.0);

void clampvector(in vec4 vector, out vec4 result) {
    result.x = clamp(vector.x, 0.0, 1.0);
    result.y = clamp(vector.y, 0.0, 1.0);
    result.z = clamp(vector.z, 0.0, 1.0);
    result.w = clamp(vector.w, 0.0, 1.0);
}

void main (void)
{
    //finalColor = vec4(1.0, 1.0, 0.0, 1.0);
    //vec4 color = vec4(fragTexCoord, 1.0, 1.0);
    //finalColor = texture(tex, fragTexCoord);
    vec4 color = texture(tex, fragTexCoord);
    //vec4 color = vec4(0.0, 0.0, 1.0, 1.0);
    if (color.a == 0.0) {
        discard;
    }

    vec3 finalVecNormal = vecNormal;
    finalVecNormal = normalize(finalVecNormal);
    vec3 normlight = normalize(light);

    //float angle = dot(light, vecNormal) * inversesqrt(length(light)) * inversesqrt(length(vecNormal));
    float angle = dot(normlight, finalVecNormal);
    if (length(vecNormal) == 0.0) {
        angle = -1.0;
    }
    angle = clamp((-1*angle+1)/2.0, 0.2, 1.0);
    //float angle = 1.0;
    //finalColor = color*angle;
    //vec4 lightcolor = vec4(1.0, 0.0, 0.0, 1.0);
    clampvector(vec4(color.r*angle, color.g*angle, color.b*angle, color.a), finalColor);
    //clampvector(vec4(0.0, 0.0, 1.0, 1.0), finalColor);
    //finalColor = vec4(vecNormal, 0.0);
    //finalColor = texture(bump, bumpTexCoord);
}
"""

fragshaderSimpleNoRotatingLight = """
#version 330
in vec2 fragTexCoord; //this is the texture coord
in vec3 vecNormal; // normal vector
in vec3 vecBinormal;
in vec3 vecTangent;
in vec2 bumpTexCoord; // coordinates on bump texture

out vec4 finalColor; //this is the output color of the pixel
uniform sampler2D tex;
uniform sampler2D bump;

uniform vec3 light;// = vec3(0.0, 1.0, 0.0);
vec4 ambient = vec4(0.1, 0.1, 0.1, 1.0);

void clampvector(in vec4 vector, out vec4 result) {
    result.x = clamp(vector.x, 0.0, 1.0);
    result.y = clamp(vector.y, 0.0, 1.0);
    result.z = clamp(vector.z, 0.0, 1.0);
    result.w = clamp(vector.w, 0.0, 1.0);
}

void main (void)
{
    //finalColor = vec4(1.0, 1.0, 0.0, 1.0);
    //vec4 color = vec4(fragTexCoord, 1.0, 1.0);
    //finalColor = texture(tex, fragTexCoord);
    vec4 color = texture(tex, fragTexCoord);
    //vec4 color = vec4(0.0, 0.0, 1.0, 1.0);
    if (color.a == 0.0) {
        discard;
    }

    vec3 finalVecNormal = vecNormal;
    finalVecNormal = normalize(finalVecNormal);
    vec3 normlight = normalize(light);

    //float angle = dot(light, vecNormal) * inversesqrt(length(light)) * inversesqrt(length(vecNormal));
    float angle = dot(normlight, finalVecNormal);
    if (length(vecNormal) == 0.0) {
        angle = -1.0;
    }
    
    angle = clamp((-1*angle+1)/2.0, 0.2, 1.0);
    angle = 1.0;
    //float angle = 1.0;
    //finalColor = color*angle;
    //vec4 lightcolor = vec4(1.0, 0.0, 0.0, 1.0);
    clampvector(vec4(color.r*angle, color.g*angle, color.b*angle, color.a), finalColor);
    //clampvector(vec4(0.0, 0.0, 1.0, 1.0), finalColor);
    //finalColor = vec4(vecNormal, 0.0);
    //finalColor = texture(bump, bumpTexCoord);
}
"""

def _compile_shader_with_error_report(shaderobj):
    glCompileShader(shaderobj)
    if not glGetShaderiv(shaderobj, GL_COMPILE_STATUS):
        raise RuntimeError(str(glGetShaderInfoLog(shaderobj), encoding="ascii"))


def create_default_shader():
    #print(glGetString(GL_VENDOR))
    vertexShaderObject = glCreateShader(GL_VERTEX_SHADER)
    fragmentShaderObject = glCreateShader(GL_FRAGMENT_SHADER)
    #glShaderSource(vertexShaderObject, 1, vertshader, len(vertshader))
    #glShaderSource(fragmentShaderObject, 1, fragshader, len(fragshader))
    glShaderSource(vertexShaderObject, vertshader)
    glShaderSource(fragmentShaderObject, fragshader)

    _compile_shader_with_error_report(vertexShaderObject)
    _compile_shader_with_error_report(fragmentShaderObject)
    
    program = glCreateProgram()

    glAttachShader(program, vertexShaderObject)
    glAttachShader(program, fragmentShaderObject)

    glLinkProgram(program)

    return program


def create_shader(vertshader, fragshader):
    # print(glGetString(GL_VENDOR))
    vertexShaderObject = glCreateShader(GL_VERTEX_SHADER)
    fragmentShaderObject = glCreateShader(GL_FRAGMENT_SHADER)
    # glShaderSource(vertexShaderObject, 1, vertshader, len(vertshader))
    # glShaderSource(fragmentShaderObject, 1, fragshader, len(fragshader))
    glShaderSource(vertexShaderObject, vertshader)
    glShaderSource(fragmentShaderObject, fragshader)

    _compile_shader_with_error_report(vertexShaderObject)
    _compile_shader_with_error_report(fragmentShaderObject)

    program = glCreateProgram()

    glAttachShader(program, vertexShaderObject)
    glAttachShader(program, fragmentShaderObject)

    glLinkProgram(program)

    return program