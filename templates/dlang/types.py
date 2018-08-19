TYPES = """\
/**
 * Dlang vulkan type definitions
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.types;

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


// version functions / macros
pure {{
    uint VK_MAKE_VERSION( uint major, uint minor, uint patch ) {{ return ( major << 22 ) | ( minor << 12 ) | ( patch ); }}
    uint VK_VERSION_MAJOR( uint ver ) {{ return ver >> 22; }}
    uint VK_VERSION_MINOR( uint ver ) {{ return ( ver >> 12 ) & 0x3ff; }}
    uint VK_VERSION_PATCH( uint ver ) {{ return ver & 0xfff; }}
}}

// Linkage of debug and allocation callbacks
extern( System ):

// Version of corresponding c header file
{HEADER_VERSION}

enum VK_NULL_HANDLE = null;

enum VK_DEFINE_HANDLE( string name ) = "struct " ~ name ~ "_handle; alias " ~ name ~ " = " ~ name ~ "_handle*;";

version( X86_64 ) {{
    alias VK_DEFINE_NON_DISPATCHABLE_HANDLE( string name ) = VK_DEFINE_HANDLE!name;
    enum VK_NULL_ND_HANDLE = null;
}} else {{
    enum VK_DEFINE_NON_DISPATCHABLE_HANDLE( string name ) = "alias " ~ name ~ " = ulong;";
    enum VK_NULL_ND_HANDLE = 0uL;
}}
{TYPE_DEFINITIONS}\

"""