STATIC_IF_EXTENSION = """
{IND}// VK_{EXTENSION}{COMMENT}
{IND}{ELSE_PREFIX}static if( __traits( isSame, extension, {EXTENSION} )) {OPEN_FORMAT}{{
{SECTIONS}
{IND}}}{CLOSE_FORMAT}
"""


PLATFORM_EXTENSIONS = """\
/**
 * Dlang vulkan platform specific types and functions as mixin template
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.platform_extensions;

/// define platform extension names as enums
/// these enums can be used directly in Platform_Extensions mixin template
{PLATFORM_EXTENSIONS}


/// extensions to a specific platform are grouped in these enum sequences
import std.meta : AliasSeq;
{PLATFORM_PROTECTIONS}


/// instantiate platform and extension specific code with this mixin template
/// required types and data structures must be imported into the module where
/// this template is instantiated
mixin template Platform_Extensions( extensions... ) {{

{IND}// publicly import erupted package modules
{IND}public import {PACKAGE_PREFIX}.types;
{IND}public import {PACKAGE_PREFIX}.functions;
{IND}import {PACKAGE_PREFIX}.dispatch_device;

{IND}// mixin function linkage, nothrow and @nogc attributes for subsecuent functions
{IND}extern(System) nothrow @nogc:

{IND}// remove duplicates from alias sequence
{IND}// this might happen if a platform extension collection AND a single extension, which is included in the collection, was specified
{IND}// e.g.: mixin Platform_Extensions!( VK_USE_PLATFORM_WIN32_KHR, VK_KHR_external_memory_win32 );
{IND}import std.meta : NoDuplicates;
{IND}alias noDuplicateExtensions = NoDuplicates!extensions;

{IND}// 1. loop through alias sequence and mixin corresponding
{IND}// extension types, aliased function pointer type definitions and __gshared function pointer declarations
{IND}static foreach( extension; noDuplicateExtensions ) {{
{TYPE_DEFINITIONS}

{IND}{IND}__gshared {{
{FUNC_DECLARATIONS}
{IND}{IND}}}
{IND}}}

{IND}// workaround for not being able to mixin two overloads with the same symbol name
{IND}alias loadDeviceLevelFunctionsExt = loadDeviceLevelFunctionsExtI;
{IND}alias loadDeviceLevelFunctionsExt = loadDeviceLevelFunctionsExtD;

{IND}// backwards compatibility aliases
{IND}alias loadInstanceLevelFunctions = loadInstanceLevelFunctionsExt;
{IND}alias loadDeviceLevelFunctions = loadDeviceLevelFunctionsExt;
{IND}alias DispatchDevice = DispatchDeviceExt;

{IND}// compose loadInstanceLevelFunctionsExt function out of unextended
{IND}// loadInstanceLevelFunctions and additional function pointers from extensions
{IND}void loadInstanceLevelFunctionsExt( VkInstance instance ) {{

{IND}{IND}// first load all non platform related function pointers from implementation
{IND}{IND}{PACKAGE_PREFIX}.functions.loadInstanceLevelFunctions( instance );

{IND}{IND}// 2. loop through alias sequence and mixin corresponding
{IND}{IND}// instance level function pointer definitions
{IND}{IND}static foreach( extension; noDuplicateExtensions ) {{
{INSTANCE_LEVEL_FUNCS}
{IND}{IND}}}
{IND}}}

{IND}// compose instance based loadDeviceLevelFunctionsExtI function out of unextended
{IND}// loadDeviceLevelFunctions and additional function pointers from extensions
{IND}// suffix I is required, as we cannot mixin mixin two overloads with the same symbol name (any more!)
{IND}void loadDeviceLevelFunctionsExtI( VkInstance instance ) {{

{IND}{IND}// first load all non platform related function pointers from implementation
{IND}{IND}{PACKAGE_PREFIX}.functions.loadDeviceLevelFunctions( instance );

{IND}{IND}// 3. loop through alias sequence and mixin corresponding
{IND}{IND}// instance based device level function pointer definitions
{IND}{IND}static foreach( extension; noDuplicateExtensions ) {{
{DEVICE_I_LEVEL_FUNCS}
{IND}{IND}}}
{IND}}}

{IND}// compose device based loadDeviceLevelFunctionsExtD function out of unextended
{IND}// loadDeviceLevelFunctions and additional function pointers from extensions
{IND}// suffix D is required as, we cannot mixin mixin two overloads with the same symbol name (any more!)
{IND}void loadDeviceLevelFunctionsExtD( VkDevice device ) {{

{IND}{IND}// first load all non platform related function pointers from implementation
{IND}{IND}loadDeviceLevelFunctions( device );

{IND}{IND}// 4. loop through alias sequence and mixin corresponding
{IND}{IND}// device based device level function pointer definitions
{IND}{IND}static foreach( extension; noDuplicateExtensions ) {{
{DEVICE_D_LEVEL_FUNCS}
{IND}{IND}}}
{IND}}}

{IND}// compose extended dispatch device out of unextended original dispatch device with
{IND}// extended, device based loadDeviceLevelFunctionsExt member function,
{IND}// device and command buffer based function pointer decelerations
{IND}struct DispatchDeviceExt {{

{IND}{IND}// use unextended dispatch device from module {PACKAGE_PREFIX}.functions as member and alias this
{IND}{IND}{PACKAGE_PREFIX}.dispatch_device.DispatchDevice commonDispatchDevice;
{IND}{IND}alias commonDispatchDevice this;

{IND}{IND}// Constructor forwards parameter 'device' to 'loadDeviceLevelFunctionsExt'
{IND}{IND}this( VkDevice device ) {{
{IND}{IND}{IND}loadDeviceLevelFunctionsExt( device );
{IND}{IND}}}

{IND}{IND}// backwards compatibility alias
{IND}{IND}alias loadDeviceLevelFunctions = loadDeviceLevelFunctionsExt;

{IND}{IND}// compose device based loadDeviceLevelFunctionsExt member function out of unextended
{IND}{IND}// loadDeviceLevelFunctions and additional member function pointers from extensions
{IND}{IND}void loadDeviceLevelFunctionsExt( VkDevice device ) {{

{IND}{IND}{IND}// first load all non platform related member function pointers of wrapped commonDispatchDevice
{IND}{IND}{IND}commonDispatchDevice.loadDeviceLevelFunctions( device );

{IND}{IND}{IND}// 5. loop through alias sequence and mixin corresponding
{IND}{IND}{IND}// device level member function pointer definitions of this wrapping DispatchDevice
{IND}{IND}{IND}static foreach( extension; noDuplicateExtensions ) {{
{DISPATCH_MEMBER_FUNCS}
{IND}{IND}{IND}}}
{IND}{IND}}}

{IND}{IND}// 6. loop through alias sequence and mixin corresponding convenience member functions
{IND}{IND}// omitting device parameter of this wrapping DispatchDevice. Member vkDevice of commonDispatchDevice is used instead
{IND}{IND}static foreach( extension; noDuplicateExtensions ) {{
{DISPATCH_CONVENIENCE_FUNCS}
{IND}{IND}}}

{IND}{IND}// 7. loop last time through alias sequence and mixin corresponding function pointer declarations
{IND}{IND}static foreach( extension; noDuplicateExtensions ) {{
{DISPATCH_FUNC_DECLARATIONS}
{IND}{IND}}}
{IND}}}
}}"""


