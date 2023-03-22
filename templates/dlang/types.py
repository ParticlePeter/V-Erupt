TYPES = """\
/**
 * Dlang vulkan type definitions
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.types;

import std.bitmanip : bitfields;

nothrow @nogc:

// defined in vk_platform.h
alias uint8_t   = ubyte;
alias uint16_t  = ushort;
alias uint32_t  = uint;
alias uint64_t  = ulong;
alias int8_t    = byte;
alias int16_t   = short;
alias int32_t   = int;
alias int64_t   = long;


enum VK_NULL_HANDLE = null;

enum VK_DEFINE_HANDLE( string name ) = "struct " ~ name ~ "_T; alias " ~ name ~ " = " ~ name ~ "_T*;";

version( D_LP64 ) {{
    alias VK_DEFINE_NON_DISPATCHABLE_HANDLE( string name ) = VK_DEFINE_HANDLE!name;
    enum VK_NULL_ND_HANDLE = null;
}} else {{
    enum VK_DEFINE_NON_DISPATCHABLE_HANDLE( string name ) = "alias " ~ name ~ " = ulong;";
    enum VK_NULL_ND_HANDLE = 0uL;
}}


deprecated( "These defines have been derecated, use VK_MAKE_API_VERSION and VK_API_ variants instead!" ) {{
    // version functions / macros
    pure {{
        uint VK_MAKE_VERSION( uint major, uint minor, uint patch ) {{ return ( major << 22 ) | ( minor << 12 ) | ( patch ); }}
        uint VK_VERSION_MAJOR( uint ver ) {{ return ver >> 22; }}
        uint VK_VERSION_MINOR( uint ver ) {{ return ( ver >> 12 ) & 0x3ff; }}
        uint VK_VERSION_PATCH( uint ver ) {{ return ver & 0xfff; }}
    }}
}}

// version functions / macros
pure {{
    uint VK_MAKE_API_VERSION( uint variant, uint major, uint minor, uint patch ) {{ return ( variant << 29 ) | ( major << 22 ) | ( minor << 12 ) | ( patch ); }}
    uint VK_API_VERSION_VARIANT( uint ver ) {{ return ver >> 29; }}
    uint VK_API_VERSION_MAJOR( uint ver ) {{ return ( ver >> 22 ) & 0x7F; }}
    uint VK_API_VERSION_MINOR( uint ver ) {{ return ( ver >> 12 ) & 0x3FF; }}
    uint VK_API_VERSION_PATCH( uint ver ) {{ return ver & 0xFFF; }}
}}

// Vulkan 1.0 version number
enum VK_API_VERSION_1_0 = VK_MAKE_API_VERSION( 0, 1, 0, 0 );  // Patch version should always be set to 0

// Linkage of debug and allocation callbacks
extern( System ):

{HEADER_VERSION}

{TYPE_DEFINITIONS}\

"""
