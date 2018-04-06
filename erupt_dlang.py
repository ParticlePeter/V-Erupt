#!/usr/bin/env python3
"""
D Vulkan bindings generator, based off of and using the Vulkan-Docs code.

to generate bindings run: vkdgen.py path/to/vulcan-docs outputDir
"""

import sys
import re
import os
from os import path
from itertools import islice

from templates.dlang.types import *
from templates.dlang.package import *
from templates.dlang.functions import *
from templates.dlang.dispatch_device import *
from templates.dlang.vulkan_lib_loader import *
from templates.dlang.platform_extensions import *



if len( sys.argv ) > 2 and not sys.argv[ 2 ].startswith( '--' ):
    sys.path.append( sys.argv[ 1 ] + '/xml/' )


try:
    from reg import *
    from generator import OutputGenerator, GeneratorOptions, write
except ImportError as e:
    print( 'Could not import Vulkan generator; please ensure that the first argument points to Vulkan-Docs directory', file = sys.stderr )
    print( '-----', file = sys.stderr )
    raise


def getFullType( elem, self = None ):
    elem_typ    = elem.find( 'type' )
    elem_str    = ( elem.text or '' ).lstrip()
    type_str    = elem_typ.text.strip()
    tail_str    = ( elem_typ.tail or '' ).rstrip()
    result      = elem_str + type_str + tail_str

    # catch const variations
    if tail_str.startswith( '* c' ):    # double const
        result = 'const( {0}* )*'.format( type_str )

    elif tail_str == '*' and elem_str:  # single const
        result = 'const( {0} )*'.format( type_str )

    # catch opaque structs, currently it
    # converts: struct wl_display* -> wl_display*
    # converts: struct wl_surface* -> wl_surface*
    if result.startswith( 'struct' ):
        result = type_str.lstrip( 'struct ' )

    # catch array types
    enum = elem.find( 'enum' )
    if enum is None:    # integral array size
        result += ( elem.find( 'name' ).tail or '' )
    else:               # enum array size
        result = '{0}[ {1} ]'.format( result, enum.text )

    #if self and tail_str:
    #    self.tests_file_content += '{0} : {1} : {2} : {0}{1}{2} : {3}\n'.format( elem_str.ljust( 6 ), type_str.ljust( 40 ), tail_str.ljust( 8 ), result )

    # this code is here to compare between old (regex) way and new way to convert const types
    # Converts C const syntax to D const syntax
    #re_double_const = re.compile(r'^const\s+(.+)\*\s+const\*\s*$')
    #reg_result  = elem_str + type_str + tail_str                    # put these out of function scope to increase build speed
    #doubleConstMatch = re.match( re_double_const, reg_result )
    #if doubleConstMatch:
    #    reg_result = 'const( {0}* )*'.format( doubleConstMatch.group( 1 ))
    #else:
    #    re_single_const = re.compile(r'^const\s+(.+)\*\s*$')        # put these out of function scope to increase build speed
    #    singleConstMatch = re.match( re_single_const, reg_result )
    #    if singleConstMatch:
    #        reg_result = 'const( {0} )*'.format( singleConstMatch.group( 1 ))
    #if self and reg_result and result == reg_result:
    #    self.tests_file_content += '{0} == {1}\n'.format( result.ljust( 50 ), reg_result )

    return result



class DGenerator( OutputGenerator ):

    def __init__( self, errFile = sys.stderr, warnFile = sys.stderr, diagFile = sys.stderr ):
        super().__init__( errFile, warnFile, diagFile )

        self.indent = 4 * ' '
        self.header_version = ''

        self.max_func_name_len = 0
        self.max_g_func_name_len = 0
        self.max_i_func_name_len = 0
        self.max_d_func_name_len = 0

        self.feature_order = []
        self.feature_content = dict()

        self.platform_extension_order = []
        self.platform_protection_order = []
        self.platform_extension_protection = dict()
        self.platform_name_protection = dict()


    # start processing
    def beginFile( self, genOpts ):
        self.genOpts = genOpts
        self.indent = genOpts.indentString
        try:
            os.mkdir( genOpts.directory )
        except FileExistsError:
            pass


        # open test file here, we might circumvent tests_file_content and write directly to the file
        #self.tests_file_content = ''
        #self.tests_file = open( 'test.txt', 'w', encoding = 'utf-8' )


        # since v1.1.70 we only get platform names per feature, but not their protect string
        # these are stored in vk.xml in platform tags, we extract them and map
        # platform name to platform protection
        for platform in self.registry.tree.findall( 'platforms/platform' ):
            self.platform_name_protection[ platform.get( 'name' ) ] = platform.get( 'protect' )



    # end processing, store data to files
    def endFile( self ):

        # -------------------- #
        # write package.d file #
        # -------------------- #

        with open( path.join( self.genOpts.directory, 'package.d' ), 'w', encoding = 'utf-8' ) as d_module:
            write( PACKAGE_HEADER.format( PACKAGE_PREFIX = self.genOpts.packagePrefix ), file = d_module )



        # ------------------ #
        # write types.d file #
        # ------------------ #

        # helper function to join function sections into format substitutions
        def typesSection():
            result = ''

            # some of the sections need formating before being merged into one code block
            # in these cases the  substitute parameter will contain the corresponding term
            for feature in self.feature_order:
                feature_section = self.feature_content[ feature ][ 'Type_Definitions' ]
                if feature_section:
                    result += '\n// - {0} -\n{1}\n'.format( feature, '\n'.join( feature_section ))

            return result[:-1]

        # types file format string, substitute format tokens with accumulated section data
        file_content = TYPES.format(
            PACKAGE_PREFIX      = self.genOpts.packagePrefix,
            HEADER_VERSION      = self.header_version,
            TYPE_DEFINITIONS    = typesSection(),
        )

        with open( path.join( self.genOpts.directory, 'types.d' ), 'w', encoding = 'utf-8' ) as d_module:
            write( file_content, file = d_module )



        # ----------------- #
        # justify functions #
        # ----------------- #

        # loop through all functions of all features and align their names
        # in the outer loop are tree categories, each category has a different per feature count of functions items
        # we store the function name length in only one function item, it can be reused with the other items in the same category
        # the items which store the name length are tuples of ( func item string, func name length )
        # the others are simply func item strings
        for value in self.feature_content.values():

            # function type aliases: alias PFN_vkFuncName = return_type function( params );
            # function declarations: PFN_vkFuncName = vkFuncName
            for i in range( len( value[ 'Func_Type_Aliases' ] )):
                lj = self.max_func_name_len       - value[ 'Func_Type_Aliases' ][ i ][ 1 ]
                value[ 'Func_Type_Aliases' ][ i ] = value[ 'Func_Type_Aliases' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )
                value[ 'Func_Declarations' ][ i ] = value[ 'Func_Declarations' ][ i ].format( LJUST_NAME = lj * ' ' )

            # global function aliases for extensions merged into vulkan 1.1: alias vkFuncNameKHR = vkFuncName;
            for i in range( len( value[ 'Func_Aliases' ] )):
                lj = self.max_func_name_len  - value[ 'Func_Aliases' ][ i ][ 1 ] + 6 # length of alias_
                value[ 'Func_Aliases' ][ i ] = value[ 'Func_Aliases' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )

            # global level functions: vkFuncName = cast( PFN_vkFuncName ) vkGetInstanceProcAddr( instance, "vkFuncName" );
            for i in range( len( value[ 'Load_G_Funcs' ] )):
                lj = self.max_g_func_name_len - value[ 'Load_G_Funcs' ][ i ][ 1 ]
                value[ 'Load_G_Funcs' ][ i ]  = value[ 'Load_G_Funcs' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )

            # instance level functions: vkFuncName = cast( PFN_vkFuncName ) vkGetInstanceProcAddr( instance, "vkFuncName" );
            for i in range( len( value[ 'Load_I_Funcs' ] )):
                lj = self.max_i_func_name_len  - value[ 'Load_I_Funcs' ][ i ][ 1 ]
                value[ 'Load_I_Funcs' ][ i ] = value[ 'Load_I_Funcs' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )

            # device level functions: vkFuncName = cast( PFN_vkFuncName ) vkGetDeviceProcAddr( device, "vkFuncName" );
            # dispatch declarations:  return_type FuncName( params ) { return vkFuncName( device, params ); }
            for i in range( len( value[ 'Load_D_Funcs' ] )):
                lj = self.max_d_func_name_len     - value[ 'Load_D_Funcs' ][ i ][ 1 ]
                value[ 'Load_D_Funcs'      ][ i ] = value[ 'Load_D_Funcs' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )
                value[ 'Disp_Declarations' ][ i ] = value[ 'Disp_Declarations' ][ i ].format( LJUST_NAME = lj * ' ' )

            # dispatch device convenience function aliases for extensions merged into vulkan 1.1: alias FuncNameKHR = FuncName;
            for i in range( len( value[ 'Conven_Aliases' ] )):
                lj = self.max_d_func_name_len  - value[ 'Conven_Aliases' ][ i ][ 1 ] + 6 # length of alias_
                value[ 'Conven_Aliases' ][ i ] = value[ 'Conven_Aliases' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )

            # dispatch device function aliases for extensions merged into vulkan 1.1: alias vkFuncNameKHR = vkFuncName;
            for i in range( len( value[ 'Disp_Aliases' ] )):
                lj = self.max_d_func_name_len - value[ 'Disp_Aliases' ][ i ][ 1 ] + 6 # length of alias_
                value[ 'Disp_Aliases' ][ i ]  = value[ 'Disp_Aliases' ][ i ][ 0 ].format( LJUST_NAME = lj * ' ' )



        # ---------------------- #
        # write functions.d file #
        # ---------------------- #

        # helper function to join function sections into format substitutions
        def functionSection( section, indent, Instance_or_Device = '' ):
            result = ''
            joiner = '\n' + indent

            # some of the sections need formating before being merged into one code block
            # in these cases the  substitute parameter will contain the corresponding term
            for feature in self.feature_order:
                feature_section = self.feature_content[ feature ][ section ]
                if feature_section:
                    result += '\n{0}// {1}\n{0}{2}\n'.format( indent, feature, joiner.join( feature_section ))

            # some of the sections need formating before being merged into one code block
            # in these cases the  substitute parameter will contain the corresponding term
            if Instance_or_Device:
                result = result.format( INSTANCE_OR_DEVICE = Instance_or_Device, instance_or_device = Instance_or_Device.lower())

            return result[:-1]


        # functions file format string, substitute format tokens with accumulated section data
        file_content = FUNCS.format(
            IND = self.indent,
            PACKAGE_PREFIX              = self.genOpts.packagePrefix,
            FUNC_TYPE_ALIASES           = functionSection( 'Func_Type_Aliases', self.indent ),
            FUNC_DECLARATIONS           = functionSection( 'Func_Declarations', self.indent ) + '\n' \
                                        + functionSection( 'Func_Aliases'     , self.indent ),
            GLOBAL_LEVEL_FUNCS          = functionSection( 'Load_G_Funcs'     , self.indent ),
            INSTANCE_LEVEL_FUNCS        = functionSection( 'Load_I_Funcs'     , self.indent ),
            DEVICE_I_LEVEL_FUNCS        = functionSection( 'Load_D_Funcs'     , self.indent,     'Instance' ),
            DEVICE_D_LEVEL_FUNCS        = functionSection( 'Load_D_Funcs'     , self.indent,     'Device'   ),
            DISPATCH_MEMBER_FUNCS       = functionSection( 'Load_D_Funcs'     , self.indent * 2, 'Device'   ),
            DISPATCH_CONVENIENCE_FUNCS  = functionSection( 'Conven_Funcs'     , self.indent ),
            DISPATCH_FUNC_DECLARATIONS  = functionSection( 'Disp_Declarations', self.indent ),
        )


        # open, write and close functions.d file
        with open( path.join( self.genOpts.directory, 'functions.d' ), 'w', encoding = 'utf-8' ) as d_module:
            write( file_content, file = d_module )



        # ---------------------------- #
        # write dispatch_device.d file #
        # ---------------------------- #

        # functions file format string, substitute format tokens with accumulated section data
        file_content = DISPATCH_DEVICE.format(
            IND = self.indent,
            PACKAGE_PREFIX              = self.genOpts.packagePrefix,
            DISPATCH_MEMBER_FUNCS       = functionSection( 'Load_D_Funcs'     , self.indent * 2, 'Device'   ),
            DISPATCH_CONVENIENCE_FUNCS  = functionSection( 'Conven_Funcs'     , self.indent ) + '\n' \
                                        + functionSection( 'Conven_Aliases'   , self.indent ),
            DISPATCH_FUNC_DECLARATIONS  = functionSection( 'Disp_Declarations', self.indent ) + '\n' \
                                        + functionSection( 'Disp_Aliases'     , self.indent ),
        )


        # open, write and close functions.d file
        with open( path.join( self.genOpts.directory, 'dispatch_device.d' ), 'w', encoding = 'utf-8' ) as d_module:
            write( file_content, file = d_module )



        # -------------------------------- #
        # write platform_extensions.d file #
        # -------------------------------- #

        # helper function to construct AliasSequnces of extension enums
        def platformProtectionAlias():
            max_protect_len = len( max( self.platform_protection_order, key=lambda p: len( p )))
            result = ''
            for protection in self.platform_protection_order:
                result += 'alias {0} = AliasSeq!( {1} );\n'.format( protection[3:].ljust( max_protect_len - 3 ), self.platform_extension_protection[ protection ] )
            return result


        # helper function to populate a (else) static if block with corresponding code
        def platformExtensionSection( sections, indent = '', comment = '', Instance_or_Device = '' ):
            result = ''
            else_prefix  = ''
            open_format  = ''
            close_format = ''

            # some sections include additional format strings which we must with escape with these
            if Instance_or_Device:
                open_format  = '{'
                close_format = '}'

            # We want to merge of Type_Definitions and Func_Type_Aliases
            # hence we wrap each section parameter into a list

            joiner = '\n' + indent + self.indent
            for extension in self.platform_extension_order:
                # We want to merge of Type_Definitions and Func_Type_Aliases into one static if block
                # hence we pass each section type as a list so we can combine several of them first
                extension_section = []
                for section in sections:
                    extension_section += self.feature_content[ extension ][ section ]

                if extension_section:
                    result += STATIC_IF_EXTENSION.format(
                        IND             = indent,
                        EXTENSION       = extension[3:],
                        COMMENT         = comment,
                        OPEN_FORMAT     = open_format,
                        ELSE_PREFIX     = else_prefix,
                        SECTIONS        = indent + self.indent + joiner.join( extension_section ),
                        CLOSE_FORMAT    = close_format,
                    )
                    else_prefix = 'else '

            # some of the sections need formating before being merged into one code block
            # in these cases the substitute parameter will contain the corresponding term
            if Instance_or_Device:
                result = result.format( INSTANCE_OR_DEVICE = Instance_or_Device, instance_or_device = Instance_or_Device.lower())

            return result[:-1]  # omit the final line break


        # platform_extensions file format string, substitute format tokens with accumulated section data
        file_content = PLATFORM_EXTENSIONS.format(
            IND = self.indent,
            PACKAGE_PREFIX              = self.genOpts.packagePrefix,
            PLATFORM_EXTENSIONS         = 'enum {0};'.format( ';\nenum '.join( [ extension[3:] for extension in self.platform_extension_order ] )),
            PLATFORM_PROTECTIONS        = platformProtectionAlias(),
            TYPE_DEFINITIONS            = platformExtensionSection( [ 'Type_Definitions', 'Func_Type_Aliases' ], 2 * self.indent, ' : types and function pointer type aliases' ),
            FUNC_DECLARATIONS           = platformExtensionSection( [ 'Func_Declarations' ] , 3 * self.indent, ' : function pointer decelerations' ),
            INSTANCE_LEVEL_FUNCS        = platformExtensionSection( [ 'Load_I_Funcs'      ] , 3 * self.indent, ' : load instance level function definitions' ),
            DEVICE_I_LEVEL_FUNCS        = platformExtensionSection( [ 'Load_D_Funcs'      ] , 3 * self.indent, ' : load instance based device level function definitions', 'Instance' ),
            DEVICE_D_LEVEL_FUNCS        = platformExtensionSection( [ 'Load_D_Funcs'      ] , 3 * self.indent, ' : load device based device level function definitions'  , 'Device' ),
            DISPATCH_MEMBER_FUNCS       = platformExtensionSection( [ 'Load_D_Funcs'      ] , 4 * self.indent, ' : load dispatch device member function definitions'     , 'Device' ),
            DISPATCH_CONVENIENCE_FUNCS  = platformExtensionSection( [ 'Conven_Funcs'      ] , 3 * self.indent, ' : dispatch device convenience member functions' ),
            DISPATCH_FUNC_DECLARATIONS  = platformExtensionSection( [ 'Func_Declarations' ] , 3 * self.indent, ' : dispatch device member function pointer decelerations'  )
            )


        with open( path.join( self.genOpts.directory, 'platform_extensions.d' ), 'w', encoding = 'utf-8' ) as d_module:
            write( file_content, file = d_module )



        # ------------------------------ #
        # write vulkan_lib_loader.d file #
        # ------------------------------ #
        with open( path.join( self.genOpts.directory, 'vulkan_lib_loader.d' ), 'w', encoding = 'utf-8' ) as d_module:
            write( LIB_LOADER.format( PACKAGE_PREFIX = self.genOpts.packagePrefix, IND = self.indent ), file = d_module )



        # write and close remaining tests data into tests.txt file
        #write( self.tests_file_content, file = self.tests_file )
        #self.tests_file.close()



    # This is an ordered list of sections in the header file.
    TYPE_SECTIONS = [ 'include', 'define', 'basetype', 'handle', 'enum', 'group', 'bitmask', 'funcpointer', 'struct' ]
    ALL_SECTIONS = TYPE_SECTIONS + ['commandPointer', 'command']


    # begin parsing of all types and functions of a certain feature / extension
    def beginFeature( self, interface, emit ):
        OutputGenerator.beginFeature( self, interface, emit )

        platform = interface.get( 'platform' )
        protection = self.platform_name_protection.get( platform, None )

        if protection:

            # some features are protected with the same protection, we want them only once in list
            if protection not in self.platform_protection_order:
                self.platform_protection_order.append( protection )

            # collect all features belonging to one protection in a string. Will be used in module platform_extensions
            if protection not in self.platform_extension_protection:
                self.platform_extension_protection[ protection ] = self.featureName[3:];
            else:
                self.platform_extension_protection[ protection ] += ', {0}'.format( self.featureName[3:] )

            # handle the current feature as platform extension
            self.platform_extension_order.append( self.featureName )

        else:
            # feature is not protected -> handle as normal types and functions
            self.feature_order.append( self.featureName )

        self.feature_content[ self.featureName ]  = {
            'Type_Definitions' : [ 'enum {0} = 1;\n'.format( self.featureName ) ],
            'Func_Type_Aliases' : [],
            'Func_Declarations' : [],
            'Func_Aliases' : [],
            'Load_G_Funcs' : [],
            'Load_I_Funcs' : [],
            'Load_D_Funcs' : [],
            'Conven_Funcs' : [],
            'Conven_Aliases' : [],
            'Disp_Declarations' : [],
            'Disp_Aliases' : []
        }
        self.sections = dict( [ ( section, [] ) for section in self.ALL_SECTIONS ] )


    # end parsing of all types and functions of a certain feature / extension
    def endFeature( self ):

        # exit this function if content is not supposed to be emitted
        if not self.emit: return

        #self.tests_file_content += self.featureName + '\n'
        #TYPE_SECTIONS = [
        #   'include', 'define', 'basetype', 'handle', 'enum', 'group', 'bitmask', 'funcpointer', 'struct' ]
        #self.tests_file_content += '\n'.join( self.sections[ 'basetype' ] )
        #self.tests_file_content += '\n'.join( self.sections[ 'handle' ] )
        #self.tests_file_content += '\n'.join( self.sections[ 'enum' ] ) + '\n\n'
        #self.tests_file_content += '\n'.join( self.sections[ 'group' ] )
        #self.tests_file_content += '\n'.join( self.sections[ 'bitmask' ] )
        #self.tests_file_content += '\n'.join( self.sections[ 'funcpointer' ] )
        #self.tests_file_content += '\n'.join( self.sections[ 'struct' ] )

        # combine all type sections
        file_content_list = []

        for section in self.TYPE_SECTIONS:
            if self.sections[ section ]:
                file_content_list += self.sections[ section ] + [ '' ]

        self.feature_content[ self.featureName ][ 'Type_Definitions' ] += file_content_list
        file_content_list = []


        # Finish processing in superclass
        OutputGenerator.endFeature( self )


    # Append a definition to the specified section
    def appendSection( self, section, text ):
        self.sections[ section ].append( text )



    def genType( self, typeinfo, name, alias ):
        super().genType( typeinfo, name, alias )

        if 'requires' in typeinfo.elem.attrib:
            required = typeinfo.elem.attrib[ 'requires' ]
            if required.endswith( '.h' ):
                return
            elif required == 'vk_platform':
                return


        if 'category' not in typeinfo.elem.attrib:
            #for k, v in typeinfo.elem.attrib.items():
            #   self.tests_file_content += '{0} : {1}'.format( k, v )
            return

        category = typeinfo.elem.get( 'category' )

        if alias:
            self.appendSection( category, 'alias {0} = {1};'.format( name, alias ))
            return


        if category == 'define':
            if name.startswith( 'VK_API_VERSION_' ):
                api_version = name.lstrip( 'VK_API_VERSION_' )
                self.appendSection( 'define', '// Vulkan {0} version number'.format( api_version.replace( '_', '.' ) ))
                self.appendSection( 'define', 'enum {0} = VK_MAKE_VERSION( {1}, 0 );  // Patch version should always be set to 0'.format( name, api_version.replace( '_', ', ' )))

        # alias VkFlags = uint32_t;
        if category == 'basetype':
            self.appendSection( 'basetype', 'alias {0} = {1};'.format( name, typeinfo.elem.find( 'type' ).text ))

        # mixin( VK_DEFINE_HANDLE!q{VkInstance} );
        elif category == 'handle':
            self.appendSection( 'handle', 'mixin( {0}!q{{{1}}} );'.format( typeinfo.elem.find( 'type' ).text, name ))

        # alias VkFlags with ... Flags corresponding to ...FlagBits: enum VkFormatFeatureFlagBits {...}; alias VkFormatFeatureFlags = VkFlags;
        elif category == 'bitmask':
            self.appendSection( 'bitmask', 'alias {0} = VkFlags;'.format( name ))

        # alias PFN_vkAllocationFunction = void* function( ... )
        elif category == 'funcpointer':
            return_type = typeinfo.elem.text[ 8 : -13 ]
            params = ''.join( x.replace( 16 * ' ', '', 1 ) for x in islice( typeinfo.elem.itertext(), 2, None ))
            params.replace( ')', ' )' )

            if params == ')(void);' : params = ');'
            else: params = params[ 2: ].replace( ')', '\n)' ).replace( '  )', ' )' )

            if self.sections[ 'funcpointer' ]:
                self.appendSection( 'funcpointer', '' )
            self.appendSection( 'funcpointer', 'alias {0} = {1} function({2}'.format( name, return_type, params ))
            #self.tests_file_content += 'alias {0} = {1} function{2}'.format( name, return_type, params )

        # structs and unions
        elif category == 'struct' or category == 'union':
            self.genStruct( typeinfo, name, alias )

        # extract header version: enum VK_HEADER_VERSION = 69;
        elif category == 'define' and name == 'VK_HEADER_VERSION':
            for header_version in islice( typeinfo.elem.itertext(), 2, 3 ):  # get the version string from the one element list
                self.header_version = 'enum VK_HEADER_VERSION ={0};'.format( header_version )

        else:
            pass


    # structs and unions
    def genStruct( self, typeinfo, name, alias ):
        super().genStruct( typeinfo, name, alias )

        category = typeinfo.elem.attrib[ 'category' ]

        if self.sections[ 'struct' ]:
           self.appendSection( 'struct', '' )
        self.appendSection( 'struct', '{0} {1} {{'.format( category, name ))
        targetLen = 0
        memberTypeName = []

        for member in typeinfo.elem.findall( 'member' ):
            memberType = getFullType( member ).strip()
            memberName = member.find( 'name' ).text

            if memberName == 'module':
                # don't use D keyword
                memberName = '_module'

            if member.get( 'values' ):
                memberName += ' = ' + member.get( 'values' )


            # get the maximum string length of all member types
            memberTypeName.append( ( memberType, memberName ))
            targetLen = max( targetLen, len( memberType ))

        # loop second time and use maximum type string length to offset member names
        for type_name in memberTypeName:
            self.appendSection( 'struct', '{2}{0}  {1};'.format( type_name[0].ljust( targetLen ), type_name[1], self.indent ))
        self.appendSection( 'struct', '}' )


    # named and global enums and enum flag bits
    def genGroup( self, group_info, group_name, alias ):
        super().genGroup( group_info, group_name, alias )

        group_elem  = group_info.elem
        category    = group_elem.get( 'type' )
        is_enum     = category == 'enum'

        if alias:
            self.appendSection( category, 'alias {0} = {1};'.format( group_name, alias ))
            return  # its either alias xor enum group

        SNAKE_NAME = re.sub( r'([0-9a-z_])([A-Z0-9][^A-Z0-9]?)', r'\1_\2', group_name ).upper()
        #self.tests_file_content += group_name.ljust( 30 ) + ' : ' + SNAKE_NAME + '\n'

        name_prefix = SNAKE_NAME
        name_suffix = ''
        expand_suffix_match = re.search( r'[A-Z][A-Z]+$', group_name )
        if expand_suffix_match:
            name_suffix = '_' + expand_suffix_match.group()
            # Strip off the suffix from the prefix
            name_prefix = SNAKE_NAME.rsplit( name_suffix, 1 )[ 0 ]
            #self.tests_file_content += name_suffix + '\n'


        # group enums by their name
        scoped_group = 'enum ' + group_name + ' {'

        # add grouped enums to global scope
        global_group = ''

        # Loop over the nested 'enum' tags. Keep track of the min_value and
        # maximum numeric values, if they can be determined; but only for
        # core API enumerants, not extension enumerants. This is inferred
        # by looking for 'extends' attributes.
        min_name = None
        max_global_len = len( max( [ elem.get( 'name' ) for elem in group_elem.findall( 'enum' ) ], key=lambda name: len( name )))
        max_global_len = max( max_global_len, len( name_prefix ) + 13 ) # len( '_BEGIN_RANGE' ) = 12
        max_scoped_len = max_global_len + 1 # global enums are one char longer than scoped enums, hence + 1

        # somehow enum items from vulkan 1.1 and extensions end up here as parameters and collide
        # we need each enum item only once, hence we skip if the item was processed once already
        scoped_elem_set = set()

        for elem in group_elem.findall( 'enum' ):
            # Convert the value to an integer and use that to track min/max.
            # Values of form -( number ) are accepted but nothing more complex.
            # Should catch exceptions here for more complex constructs. Not yet.
            ( enum_val, enum_str ) = self.enumToValue( elem, True )
            name = elem.get( 'name' )

            # Extension enumerates are only included if they are requested
            # in addExtensions or match defaultExtensions.
            if ( elem.get( 'extname' ) is None or
                re.match( self.genOpts.addExtensions, elem.get( 'extname' )) is not None or
                self.genOpts.defaultExtensions == elem.get( 'supported' )):
                scoped_elem = '\n{0}{1} = {2},'.format( self.indent, name.ljust( max_scoped_len ), enum_str )
                if scoped_elem not in scoped_elem_set:
                    scoped_elem_set.add( scoped_elem )
                    scoped_group += scoped_elem
                    global_group += '\nenum {0} = {1}.{2};'.format( name.ljust( max_global_len ), group_name, name )

            if is_enum and elem.get( 'extends' ) is None:
                if min_name is None:
                    min_name  = max_name = name
                    min_value = max_value = enum_val
                elif enum_val < min_value:
                    min_name  = name
                    min_value = enum_val
                elif enum_val > max_value:
                    max_name  = name
                    max_value = enum_val

        # Generate min/max value tokens and a range-padding enum. Need some
        # additional padding to generate correct names...
        if is_enum:
            scoped_group += '\n' + self.indent + ( name_prefix + '_BEGIN_RANGE' + name_suffix ).ljust( max_scoped_len ) + ' = ' + min_name + ','
            scoped_group += '\n' + self.indent + ( name_prefix + '_END_RANGE'   + name_suffix ).ljust( max_scoped_len ) + ' = ' + max_name + ','
            scoped_group += '\n' + self.indent + ( name_prefix + '_RANGE_SIZE'  + name_suffix ).ljust( max_scoped_len ) + ' = ' + max_name + ' - ' + min_name + ' + 1,'

            global_group += '\nenum {0} = {1}.{2}{3}{4};'.format( ( name_prefix + '_BEGIN_RANGE' + name_suffix ).ljust( max_global_len ), group_name, name_prefix, '_BEGIN_RANGE', name_suffix )
            global_group += '\nenum {0} = {1}.{2}{3}{4};'.format( ( name_prefix + '_END_RANGE'   + name_suffix ).ljust( max_global_len ), group_name, name_prefix, '_END_RANGE'  , name_suffix )
            global_group += '\nenum {0} = {1}.{2}{3}{4};'.format( ( name_prefix + '_RANGE_SIZE'  + name_suffix ).ljust( max_global_len ), group_name, name_prefix, '_RANGE_SIZE' , name_suffix )

        scoped_group += '\n' + self.indent + ( name_prefix + '_MAX_ENUM' + name_suffix ).ljust( max_scoped_len ) + ' = 0x7FFFFFFF\n}'
        global_group += '\nenum {0} = {1}.{2}{3}{4};'.format( ( name_prefix + '_MAX_ENUM' + name_suffix ).ljust( max_global_len ), group_name, name_prefix, '_MAX_ENUM' , name_suffix )


        if is_enum:
            if self.sections[ 'group' ]:
                self.appendSection( 'group', '' )       # this empty string will be terminated with '\n' at the join operation
            self.appendSection( 'group', scoped_group + global_group )

        else:
            if self.sections[ 'bitmask' ]:
                self.appendSection( 'bitmask', '' )     # this empty string will be terminated with '\n' at the join operation
            self.appendSection( 'bitmask', scoped_group + global_group )



    # enum VK_TRUE = 1; enum VK_FALSE = 0; enum _SPEC_VERSION = ; enum _EXTENSION_NAME = ;
    def genEnum( self, enuminfo, name, alias ):
        super().genEnum( enuminfo, name, alias )

        if alias:
            self.appendSection( 'enum', 'alias {0} = {1};'.format( name, alias ))
            #self.tests_file_content += 'alias {0} = {1};\n'.format( name, alias )
            return

        _,enum_str = self.enumToValue( enuminfo.elem, False )
        if enum_str == 'VK_STRUCTURE_TYPE_DEBUG_REPORT_CALLBACK_CREATE_INFO_EXT':
            enum_str = 'VkStructureType.' + enum_str

        elif enum_str == '(~0ULL)':
            enum_str = '(~0UL)'

        self.appendSection( 'enum', 'enum {0} = {1};'.format( name, enum_str ))
        #self.tests_file_content += 'enum {0} = {1};'.format( name, enum_str ) + '\n'



    # functions
    def genCmd( self, cmdinfo, name, alias ):
        super().genCmd( cmdinfo, name, alias )

        # store get name length and store the maximum function name length
        name_len = len( name )
        self.max_func_name_len = max( self.max_func_name_len, name_len )


        # get params of this function, we require the first param type
        # before we evaluate aliases, to determine if alias ends up in dispatch device
        params  = cmdinfo.elem.findall( 'param' )
        param_0_type = getFullType( params[ 0 ] )


        # alias global and DispatchDevice functions
        if alias:

            # alias global scope functions
            self.feature_content[ self.featureName ][ 'Func_Aliases' ].append(
                ( 'alias {0}{{LJUST_NAME}} = {1};'.format( name, alias ), name_len ) )

            # alias dispatch device functions and partially device scope vulkan funcs (for VkDevice and VkCommandBuffer)
            if param_0_type in ( 'VkDevice', 'VkCommandBuffer' ):
                self.feature_content[ self.featureName ][ 'Conven_Aliases' ].append(
                    ( 'alias {0}{{LJUST_NAME}} = {1};'.format( name[2:], alias[2:] ), name_len ) )
                self.feature_content[ self.featureName ][ 'Disp_Aliases' ].append(
                    ( 'alias {0}{{LJUST_NAME}} = {1};'.format( name, alias ), name_len ) )
                self.max_d_func_name_len = max( self.max_d_func_name_len, name_len )

            # second part of device scope vulkan funcs (for VkQueue, for which no convenience fucs exist)
            elif param_0_type == 'VkQueue':
                self.feature_content[ self.featureName ][ 'Disp_Aliases' ].append(
                    ( 'alias {0}{{LJUST_NAME}} = {1};'.format( name, alias ), name_len ) )
                self.max_d_func_name_len = max( self.max_d_func_name_len, name_len )

            return  # its either alias or full functions


        # get and modify the return type to align functions for better readability
        proto = cmdinfo.elem.find( 'proto' )
        return_type = getFullType( proto ).strip()
        do_return = ''
        if return_type == 'void':   return_type = 'void    '
        else:                       do_return = 'return '


        # a parameter consist of a type and a name, here we merge all parameters into a list
        joined_params = ', '.join( getFullType( param ).strip() + ' ' + param.find( 'name' ).text for param in params )


        # construct function pointer prototypes, declarations and keep track of each function name length for aligning purpose
        # some of the function items are stored as tuple of ( func item string, func name length ), we use the latter for alignment
        # the other function items are store as func item string, their alignment parameter is the same as of their tuple predecessors
        func_type_name = 'alias PFN_{0}{{LJUST_NAME}} = {1}  function( {2} );'.format( name, return_type, joined_params )
        self.feature_content[ self.featureName ][ 'Func_Type_Aliases' ].append( ( func_type_name, name_len ) )
        self.feature_content[ self.featureName ][ 'Func_Declarations' ].append( 'PFN_{0}{{LJUST_NAME}} {0};'.format( name ))


        # ignore vkGetInstanceProcAddr, it must be loaded from implementation lib
        if name == 'vkGetInstanceProcAddr': pass


        # construct global level functions, which are used to parametrize and create a VkInstance
        elif param_0_type not in ( 'VkInstance', 'VkPhysicalDevice', 'VkDevice', 'VkQueue', 'VkCommandBuffer' ):
            self.feature_content[ self.featureName ][ 'Load_G_Funcs' ].append(
                ( '{0}{{LJUST_NAME}} = cast( PFN_{0}{{LJUST_NAME}} ) vkGetInstanceProcAddr( null, "{0}" );'.format( name ), name_len ) )
            self.max_g_func_name_len = max( self.max_g_func_name_len, name_len )


        # construct loader for instance level functions
        # vkGetDeviceProcAddr is an exception as it is an instance level function with para_0_type == 'VkDevvice'
        elif param_0_type in ( 'VkPhysicalDevice', 'VkInstance' ) or name == 'vkGetDeviceProcAddr':
            self.feature_content[ self.featureName ][ 'Load_I_Funcs' ].append(
                ( '{0}{{LJUST_NAME}} = cast( PFN_{0}{{LJUST_NAME}} ) vkGetInstanceProcAddr( instance, "{0}" );'.format( name ), name_len ) )
            self.max_i_func_name_len = max( self.max_i_func_name_len, name_len )


        # construct loader for device and instance based device level functions as well as dispatch device convenience functions
        else: # param_0_type in ( 'VkDevice', 'VkQueue', 'VkCommandBuffer' ):
            self.feature_content[ self.featureName ][ 'Load_D_Funcs' ].append(
                ( '{0}{{LJUST_NAME}} = cast( PFN_{0}{{LJUST_NAME}} ) vkGet{{{{INSTANCE_OR_DEVICE}}}}ProcAddr( {{{{instance_or_device}}}}, "{0}" );'.format( name ), name_len ) )
            self.feature_content[ self.featureName ][ 'Disp_Declarations'   ].append( 'PFN_{0}{{LJUST_NAME}} {0};'.format( name ))
            self.max_d_func_name_len = max( self.max_d_func_name_len, name_len )

            # for convenience functions we remove the first parameter if it is a VkDevice or VkCommandBuffer
            # additionally we remove the const( VkAllocationCallbacks )* pAllocator parameter
            # arguments are just the parameter names without their types, they will be used with the vk... member functions
            # VkDevice and VkAllocationCallbacks are both supplied by the DispatchDeveice
            joined_args = ''
            if len( params[1:] ):
                joined_args = ', ' + ', '.join( param.find( 'name' ).text for param in params[1:] )
            joined_params = ', '.join( getFullType( param ).strip() + ' ' + param.find( 'name' ).text
                for param in params[1:] if not getFullType( param ).strip().startswith( 'const( VkAllocationCallbacks )*' ))

            # create VkDevice convenience functions for DispatchDevice
            if param_0_type == 'VkDevice':
                convenience_func = '{0}  {1}( {2} ) {{ {3}{4}( vkDevice{5} ); }}'.format(
                    return_type, name[2:], joined_params, do_return, name, joined_args ).replace( '(  )', '()' )
                self.feature_content[ self.featureName ][ 'Conven_Funcs' ].append( convenience_func )

            # create VkCommandBuffer convenience functions for DispatchDevice
            elif param_0_type == 'VkCommandBuffer':
                convenience_func = '{0}  {1}( {2} ) {{ {3}{4}( commandBuffer{5} ); }}'.format(
                    return_type, name[2:], joined_params, do_return, name, joined_args ).replace( '(  )', '()' )
                self.feature_content[ self.featureName ][ 'Conven_Funcs' ].append( convenience_func )










# specify options for our generator
class DGeneratorOptions( GeneratorOptions ):
    def __init__( self, *args, **kwargs ):
        self.packagePrefix      = kwargs.pop( 'packagePrefix' )
        self.namePrefix         = kwargs.pop( 'namePrefix' )
        self.genFuncPointers    = kwargs.pop( 'genFuncPointers' )
        self.indentString       = kwargs.pop( 'indentString' )
        super().__init__( *args, **kwargs )



if __name__ == '__main__':
    import argparse

    vkxml = 'vk.xml'
    parser = argparse.ArgumentParser()
    if len( sys.argv ) > 2 and not sys.argv[ 2 ].startswith( '--' ):
        parser.add_argument( 'vulkandocs' )
        vkxml = sys.argv[ 1 ] + '/xml/vk.xml'

    parser.add_argument( 'outputDirectory' )
    parser.add_argument( '--packagePrefix', default = 'erupted' )
    parser.add_argument( '--namePrefix',    default = 'Erupted' )
    parser.add_argument( '--indentString',  default = '    ' )



    parser.add_argument('-defaultExtensions',   action='store',         default='vulkan',   help='Specify a single class of extensions to add to targets')
    parser.add_argument('-extension',           action='append',        default=[],         help='Specify an extension or extensions to add to targets')
    parser.add_argument('-removeExtensions',    action='append',        default=[],         help='Specify an extension or extensions to remove from targets')
    parser.add_argument('-emitExtensions',      action='append',        default=[],         help='Specify an extension or extensions to emit in targets')
    parser.add_argument('-feature',             action='append',        default=[],         help='Specify a core API feature name or names to add to targets')
    parser.add_argument('-debug',               action='store_true',                        help='Enable debugging')
    parser.add_argument('-dump',                action='store_true',                        help='Enable dump to stderr')
    parser.add_argument('-diagfile',            action='store',         default=None,       help='Write diagnostics to specified file')
    parser.add_argument('-errfile',             action='store',         default=None,       help='Write errors and warnings to specified file instead of stderr')
    parser.add_argument('-noprotect',           action='store_false',   dest='protect',     help='Disable inclusion protection in output headers')
    parser.add_argument('-profile',             action='store_true',                        help='Enable profiling')
    parser.add_argument('-registry',            action='store',         default='vk.xml',   help='Use specified registry file instead of vk.xml')
    parser.add_argument('-time',                action='store_true',                        help='Enable timing')
    parser.add_argument('-validate',            action='store_true',                        help='Enable group validation')
    parser.add_argument('-o', dest='directory', action='store',         default='.',        help='Create target and related files in specified directory')
    parser.add_argument('-quiet',               action='store_true',    default=True,       help='Suppress script output during normal execution.')
    parser.add_argument('-verbose',dest='quiet',action='store_false',   default=True,       help='Enable script output during normal execution.')
    parser.add_argument('target',               metavar='target', nargs='?',                help='Specify target')

    args = parser.parse_args()



    # Turn a list of strings into a regexp string matching exactly those strings
    def makeREstring(list, default = None):
        if len(list) > 0 or default == None:
            return '^(' + '|'.join(list) + ')$'
        else:
            return default

    # Default class of extensions to include, or None
    defaultExtensions = args.defaultExtensions

    # Additional extensions to include (list of extensions)
    extensions = args.extension

    # Extensions to remove (list of extensions)
    removeExtensions = args.removeExtensions

    # Extensions to emit (list of extensions)
    emitExtensions = args.emitExtensions

    # Features to include (list of features)
    features = args.feature

    # Whether to disable inclusion protect in headers
    protect = args.protect

    # Output target directory
    directory = args.directory

    # Descriptive names for various regexp patterns used to select
    # versions and extensions
    allFeatures     = allExtensions = '.*'
    noFeatures      = noExtensions = None

    # Turn lists of names/patterns into matching regular expressions
    addExtensionsPat     = makeREstring(extensions, None)
    removeExtensionsPat  = makeREstring(removeExtensions, None)
    emitExtensionsPat    = makeREstring(emitExtensions, allExtensions)
    featuresPat          = makeREstring(features, allFeatures)




    gen = DGenerator()
    reg = Registry()
#   reg.loadElementTree( etree.parse( vkxml ))
    reg.loadFile( vkxml )
    reg.setGenerator( gen )
    reg.apiGen(
        DGeneratorOptions(
        directory           = args.outputDirectory,
        apiname             = 'vulkan',
        profile             = None,
        versions            = '.*',     # Their: featuresPat,
        emitversions        = '.*',     # Their: featuresPat,
        defaultExtensions   = defaultExtensions,
        addExtensions       = None,         # Mine: r'.*',
        removeExtensions    = None,         #'VK_KHR_device_group|VK_KHR_external_memory_capabilities|VK_KHR_external_semaphore_capabilities', #removeExtensionsPat,
        emitExtensions      = '.*',         # Their: emitExtensionsPat,
        #prefixText         = prefixStrings + vkPrefixStrings,
        genFuncPointers     = True,
        #protectFile        = protectFile,
        #protectFeature      = False,

        indentString        = args.indentString,
        packagePrefix       = args.packagePrefix,
        namePrefix          = args.namePrefix,

        #protectProto      = '#ifndef',
        #protectProtoStr   = 'VK_NO_PROTOTYPES',
        #apicall           = 'VKAPI_ATTR ',
        #apientry          = 'VKAPI_CALL ',
        #apientryp         = 'VKAPI_PTR *',
        #alignFuncParam    = 48)
    ))


# 130: open  test file
# 343: close test file