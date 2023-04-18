VK_VIDEO = """\
/**
 * Dlang vulkan type definitions
 *
 * Copyright: Copyright 2015-2016 The Khronos Group Inc.; Copyright 2016 Alex Parrill, Peter Particle.
 * License:   $(https://opensource.org/licenses/MIT, MIT License).
 * Authors: Copyright 2016 Alex Parrill, Peter Particle
 */
module {PACKAGE_PREFIX}.vk_video;

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

{TYPE_DEFINITIONS}\

"""