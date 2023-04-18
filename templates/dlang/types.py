TYPES = """\
/**
 * Dlang vulkan type definitions
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.types;

import {PACKAGE_PREFIX}.vk_video;
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


// Linkage of debug and allocation callbacks
extern( System ):

{TYPE_DEFINITIONS}\

"""
