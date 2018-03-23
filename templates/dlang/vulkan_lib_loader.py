LIB_LOADER = """\
/**
 * Dlang vulkan lib loader retrieving vkGetInstanceProcAddr for windows and posix systems
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.vulkan_lib_loader;

import {PACKAGE_PREFIX}.functions;
import core.stdc.stdio : fprintf, stderr, FILE;

nothrow @nogc:


/// private helper functions for windows platform
version( Windows ) {{
private:
{IND}import core.sys.windows.windows;
{IND}HMODULE         vulkan_lib  = null;
{IND}auto loadLib()  {{ return LoadLibrary( "vulkan-1.dll" ); }}
{IND}auto freeLib()  {{ return FreeLibrary( vulkan_lib ) != 0; }}
{IND}auto loadSym()  {{ return cast( PFN_vkGetInstanceProcAddr )GetProcAddress( vulkan_lib, "vkGetInstanceProcAddr" ); }}
{IND}void logLibError( FILE* log_stream, const( char )* message ) {{
{IND}{IND}fprintf( log_stream, "%svulkan-1.dll! Error code: 0x%x\\n", message, GetLastError());
{IND}}}
}}


/// private helper functions for posix platforms
version( Posix ) {{
private:
{IND}import core.sys.posix.dlfcn : dlerror, dlopen, dlclose, dlsym;
{IND}void*           vulkan_lib  = null;
{IND}auto loadLib()  {{ return dlopen( "libvulkan.so.1", RTLD_LAZY | RTLD_LOCAL ); }}
{IND}auto freeLib()  {{ return dlclose( vulkan_lib ) == 0; }}
{IND}auto loadSym()  {{ return cast( PFN_vkGetInstanceProcAddr )dlsym( vulkan_lib, "vkGetInstanceProcAddr" ); }}
{IND}void logLibError( FILE* log_stream, const( char )* message ) {{
{IND}{IND}fprintf( log_stream, "%slibvulkan.so.1! Error: %s\\n", message, dlerror );
{IND}}}
}}


/// tries to load the platform vulkan dynamic link library
/// the library handle / pointer is stored privately in this module
/// errors are reported to a specifiable stream which is standard error by default
/// Params:
///     log_stream = file stream to receive error messages, default stderr
/// Returns: true if the vulkan lib could be loaded, false otherwise
bool loadVulkanLib( FILE* log_stream = stderr ) {{
{IND}vulkan_lib = loadLib;
{IND}if( !vulkan_lib ) {{
{IND}{IND}logLibError( log_stream, "Could not load " );
{IND}{IND}return false;
{IND}}} else {{
{IND}{IND}return true;
{IND}}}
}}


/// tries to load the vkGetInstanceProcAddr function from the module private lib handle / pointer
/// if the lib was not loaded so far loadVulkanLib is called
/// errors are reported to a specifiable stream which is standard error by default
/// Params:
///     log_stream = file stream to receive error messages, default stderr
/// Returns: vkGetInstanceProcAddr if it could be loaded from the lib, null otherwise
PFN_vkGetInstanceProcAddr loadGetInstanceProcAddr( FILE* log_stream = stderr ) {{
{IND}if( !vulkan_lib && !loadVulkanLib( log_stream )) {{
{IND}{IND}fprintf( log_stream, "Cannot not retrieve vkGetInstanceProcAddr as vulkan lib is not loaded!" );
{IND}{IND}return null;
{IND}}}
{IND}auto getInstanceProcAddr = loadSym;
{IND}if( !getInstanceProcAddr )
{IND}{IND}logLibError( log_stream, "Could not retrieve vkGetInstanceProcAddr from " );
{IND}return getInstanceProcAddr;
}}


/// tries to free / unload the previously loaded platform vulkan lib
/// errors are reported to a specifiable stream which is standard error by default
/// Params:
///     log_stream = file stream to receive error messages, default stderr
/// Returns: true if the vulkan lib could be freed, false otherwise
bool freeVulkanLib( FILE* log_stream = stderr ) {{
{IND}if( !vulkan_lib ) {{
{IND}{IND}fprintf( log_stream, "Cannot free vulkan lib as it is not loaded!" );
{IND}{IND}return false;
{IND}}} else if( freeLib ) {{
{IND}{IND}logLibError( log_stream, "Could not unload " );
{IND}{IND}return false;
{IND}}} else {{
{IND}{IND}return true;
{IND}}}
}}


/// Combines loadVulkanLib, loadGetInstanceProcAddr and loadGlobalLevelFunctions( PFN_vkGetInstanceProcAddr )
/// from module {PACKAGE_PREFIX}.functions. If this function succeeds the function vkGetInstanceProcAddr
/// from module {PACKAGE_PREFIX}.functions can be used freely. Moreover the required functions to initialize a
/// vulkan instance a vkEnumerateInstanceExtensionProperties, vkEnumerateInstanceLayerProperties and vkCreateInstance
/// are available as well. To get all the other functions an vulkan instance must be created and with it
/// loadInstanceLevelFunctions be called from either {PACKAGE_PREFIX}.functions or through a custom tailored module
/// with mixed in extensions through the {PACKAGE_PREFIX}.platform.mixin_extensions mechanism.
/// Additional device based functions can then be loaded with loadDeviceLevelFunctions passing in the instance or
/// with creating a vulkan device beforehand and calling the same function with it.
///
/// Note: as this function indirectly calls loadVulkanLib loading the vulkan lib, freeVulkanLib should be called
///       at some point in the process to cleanly free / unload the lib
/// all errors during vulkan lib loading and vkGetInstanceProcAddr retrieving are reported to log_stream, default stderr
///     log_stream = file stream to receive error messages, default stderr
/// Returns: true if the vulkan lib could be freed, false otherwise
bool loadGlobalLevelFunctions( FILE* log_stream = stderr ) {{
{IND}auto getInstanceProcAddr = loadGetInstanceProcAddr( log_stream );
{IND}if( !getInstanceProcAddr ) return false;
{IND}{PACKAGE_PREFIX}.functions.loadGlobalLevelFunctions( getInstanceProcAddr );
{IND}return true;
}}

"""

