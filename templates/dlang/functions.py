FUNCS = """\
/**
 * Dlang vulkan function pointer prototypes, declarations and loader from vkGetInstanceProcAddr
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.functions;

public import {PACKAGE_PREFIX}.types;

nothrow @nogc:


/// function type aliases
extern( System ) {{
{FUNC_TYPE_ALIASES}
}}


/// function declarations
__gshared {{
{FUNC_DECLARATIONS}
}}


/// sets vkCreateInstance function pointer and acquires basic functions to retrieve information about the implementation
/// and create an instance: vkEnumerateInstanceExtensionProperties, vkEnumerateInstanceLayerProperties, vkCreateInstance
void loadGlobalLevelFunctions( PFN_vkGetInstanceProcAddr getInstanceProcAddr ) {{
{IND}vkGetInstanceProcAddr = getInstanceProcAddr;
{GLOBAL_LEVEL_FUNCS}
}}


/// with a valid VkInstance call this function to retrieve additional VkInstance, VkPhysicalDevice, ... related functions
void loadInstanceLevelFunctions( VkInstance instance ) {{
{IND}assert( vkGetInstanceProcAddr !is null, "Function pointer vkGetInstanceProcAddr is null!\\nCall loadGlobalLevelFunctions -> loadInstanceLevelFunctions" );
{INSTANCE_LEVEL_FUNCS}
}}


/// with a valid VkInstance call this function to retrieve VkDevice, VkQueue and VkCommandBuffer related functions
/// the functions call indirectly through the VkInstance and will be internally dispatched by the implementation
/// use loadDeviceLevelFunctions( VkDevice device ) bellow to avoid this indirection and get the pointers directly form a VkDevice
void loadDeviceLevelFunctions( VkInstance instance ) {{
{IND}assert( vkGetInstanceProcAddr !is null, "Function pointer vkGetInstanceProcAddr is null!\\nCall loadGlobalLevelFunctions -> loadDeviceLevelFunctions( instance )" );
{DEVICE_I_LEVEL_FUNCS}
}}


/// with a valid VkDevice call this function to retrieve VkDevice, VkQueue and VkCommandBuffer related functions
/// the functions call directly VkDevice and related resources and can be retrieved for one and only one VkDevice
/// calling this function again with another VkDevices will overwrite the __gshared functions retrieved previously
/// see module {PACKAGE_PREFIX}.dispatch_device if multiple VkDevices will be used
void loadDeviceLevelFunctions( VkDevice device ) {{
{IND}assert( vkGetDeviceProcAddr !is null, "Function pointer vkGetDeviceProcAddr is null!\\nCall loadGlobalLevelFunctions -> loadInstanceLevelFunctions -> loadDeviceLevelFunctions( device )" );
{DEVICE_D_LEVEL_FUNCS}
}}
"""

