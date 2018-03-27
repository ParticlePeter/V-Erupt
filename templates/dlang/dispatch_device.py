DISPATCH_DEVICE = """\
/**
 * Dlang vulkan device related func loader as struct members
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.dispatch_device;

public import {PACKAGE_PREFIX}.types;
import {PACKAGE_PREFIX}.functions;

nothrow @nogc:


/// struct to group per device device level functions into a custom namespace
/// keeps track of the device to which the functions are bound
/// additionally to the device related vulkan functions, convenience functions exist
/// with same name but omitting the vk prefix as well as the first (VkDevice) parameter
/// these functions forward to their vk counterparts using the VkDevice member of the DispatchDevice
/// Moreover the same convenience functions exist for vkCmd... functions. In this case the
/// first parameter is substituted with the public member VkCommandBuffer commandBuffer,
/// which must have been set to a valid command buffer before usage.
struct DispatchDevice {{

{IND}private VkDevice                           device          = VK_NULL_HANDLE;
{IND}private const( VkAllocationCallbacks )*    allocator       = null;
{IND}VkCommandBuffer                            commandBuffer   = VK_NULL_HANDLE;


{IND}/// return copy of the internal VkDevice
{IND}VkDevice vkDevice() {{
{IND}{IND}return device;
{IND}}}


{IND}/// return const allocator address
{IND}const( VkAllocationCallbacks )* pAllocator() {{
{IND}{IND}return allocator;
{IND}}}


{IND}/// constructor forwards parameter 'device' to 'this.loadDeviceLevelFunctions'
{IND}this( VkDevice device, const( VkAllocationCallbacks )* allocator = null ) {{
{IND}{IND}this.loadDeviceLevelFunctions( device );
{IND}}}


{IND}/// load the device level member functions
{IND}/// this also sets the private member 'device' to the passed in VkDevice
{IND}/// as well as the otional host allocator
{IND}/// if a custom allocator is required it must be specified here and cannot be changed throughout the liftime of the device
{IND}/// now the DispatchDevice can be used e.g.:
{IND}///      auto dd = DispatchDevice( device );
{IND}///      dd.vkDestroyDevice( dd.vkDevice, pAllocator );
{IND}/// convenience functions to omit the first arg and the allocator do exist, see bellow
{IND}void loadDeviceLevelFunctions( VkDevice device, const( VkAllocationCallbacks )* allocator = null ) {{
{IND}{IND}assert( vkGetInstanceProcAddr !is null, "Function pointer vkGetInstanceProcAddr is null!\\nCall loadGlobalLevelFunctions -> loadInstanceLevelFunctions -> DispatchDevice.loadDeviceLevelFunctions" );
{IND}{IND}this.allocator = allocator;
{IND}{IND}this.device = device;
{DISPATCH_MEMBER_FUNCS}
{IND}}}


{IND}/// convenience member functions, forwarded to corresponding vulkan functions
{IND}/// parameters of type VkDevice, const( VkAllocationCallbacks )* and VkCommandBuffer are omitted
{IND}/// they will be supplied by the member properties vkDevice, pAllocator and the public member commandBuffer
{IND}/// e.g.:
{IND}///      auto dd = DispatchDevice( device );
{IND}///      dd.DestroyDevice();       // instead of: dd.vkDestroyDevice( dd.vkDevice, pAllocator );
{IND}///
{IND}/// Same mechanism works with functions which require a VkCommandBuffer as first arg
{IND}/// In this case the public member 'commandBuffer' must be set beforehand
{IND}/// e.g.:
{IND}///      dd.commandBuffer = some_command_buffer;
{IND}///      dd.BeginCommandBuffer( &beginInfo );
{IND}///      dd.CmdBindPipeline( VK_PIPELINE_BIND_POINT_GRAPHICS, some_pipeline );
{IND}///
{IND}/// Does not work with queues, there are just too few queue related functions
{DISPATCH_CONVENIENCE_FUNCS}


{IND}/// member function pointer decelerations
{DISPATCH_FUNC_DECLARATIONS}
}}
"""

