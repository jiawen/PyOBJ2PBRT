class Material:

    def __init__( self, name ):

        self.name = name
        self.maps = {}
        self.params = {}

    def addMap( self, mapName, filename ):
        self.maps[ mapName ] = filename

    def addValue( self, paramName, value ):
        self.params[ paramName ] = value

    def getMap( self, mapName ):
        return self.maps[ mapName ]

    def getValue( self, paramName ):
        return self.params[ paramName ]

class MaterialLibrary:

    def __init__( self ):

        self.materials = {}

    def appendMaterialsFromFile( self, filename ):

        currentMaterial = None

        f = open( filename )
        lines = f.readlines()
        f.close()

        for line in lines:
            lin = line.rstrip()
            if lin == "":
                continue

            tokens = lin.split()
            cmd = tokens[0]
            if cmd == "" or cmd == '#':
                continue
            elif cmd == 'newmtl':
                name = tokens[1]
                currentMaterial = Material( name )
                self.materials[ name ] = currentMaterial
            elif cmd.startswith( 'map_' ):
                currentMaterial.addMap( cmd[4:], tokens[1] )
            else:
                currentMaterial.addValue( cmd, [ float( tok ) for tok in tokens[1:] ] )

    def getMaterial( self, name ):
        return self.materials[ name ]

class Face:

    def __init__( self, tokens ):

        face0Tokens = tokens[1].split( '/' )
        face1Tokens = tokens[2].split( '/' )
        face2Tokens = tokens[3].split( '/' )

        self.positionIndices = [ int( face0Tokens[0] ) - 1, int( face1Tokens[0] ) - 1, int( face2Tokens[0] ) - 1 ]

        if face0Tokens[1] == '':
            self.texcoordIndices = [ -1, -1, -1 ]
        else:
            self.texcoordIndices = [ int( face0Tokens[1] ) - 1, int( face1Tokens[1] ) - 1, int( face2Tokens[1] ) - 1 ]

        if face0Tokens[2] == '':
            self.normalIndices = [ -1, -1, -1 ]
        else:
            self.normalIndices = [ int( face0Tokens[2] ) - 1, int( face1Tokens[2] ) - 1, int( face2Tokens[2] ) - 1 ]

class Group:

    def __init__( self, name ):

        self.name = name
        self.faces = []
        self.material = None

    def setMaterial( self, material ):
        self.material = material

    def getMaterial( self ):
        return self.material

    def addFace( self, face ):
        self.faces.append( face )

# All the materials
class PBRTMaterialLibrary:

    def __init__( self, materialLibrary ):

        self.textures = {}
        self.materialLibrary = materialLibrary

        # Create textures
        for materialName in materialLibrary.materials.keys():
            material = materialLibrary.getMaterial( materialName )

            for mapName in material.maps.keys():
                textureName = materialName + "_" + mapName
                self.textures[ textureName ] = material.maps[ mapName ]

    def serialize( self, filenamePrefix ):

        filename = filenamePrefix + "-mat.pbrt"
        f = open( filename, "w" )

        for textureName in self.textures.keys():
            f.write( 'Texture "%s" "color" "imagemap"\n' % textureName )
            f.write( '\t"string filename" ["%s"]\n\n' % self.textures[ textureName ] )

        for materialName in self.materialLibrary.materials.keys():
            material = self.materialLibrary.getMaterial( materialName )

            # if it contains Kd map, then, else, write Kd, else...
            f.write( 'MakeNamedMaterial "%s"\n' % materialName )
            f.write( '\t"string type" ["uber"]\n' )

            if "Kd" in material.maps:
                f.write( '\t"texture Kd" ["%s_Kd"]\n' % materialName )
            elif "Kd" in material.params:
                kd = material.getValue( "Kd" )
                f.write( '\t"color Kd" [%f %f %f]\n' % ( kd[0], kd[1], kd[2] ) )
            else:
                f.write( '\t"color Kd" [1 1 1]\n' )

            f.write( '\n' )

        f.close()



# A group with compacted indices
class PBRTShape:

    def __init__( self, mesh, group ):

        # walk over the vertex indices
        # and map them to unified list of new indices

        currentOutputIndex = 0
        inputIndexToOutputIndex = {}

        self.name = group.name
        self.material = group.getMaterial()

        self.indices = []
        self.positions = []
        self.texcoords = []
        self.normals = []

        for f in group.faces:
            for i in range(3):
                pi = f.positionIndices[i]
                ti = f.texcoordIndices[i]
                ni = f.normalIndices[i]

                # add the mapping if it doesn't exist
                # and increment
                if pi not in inputIndexToOutputIndex:
                    inputIndexToOutputIndex[ pi ] = currentOutputIndex
                    currentOutputIndex += 1

                    # since this is the first reference, write out the actual
                    # values
                    position = mesh.positions[pi]
                    self.positions.append( position )

                    texcoords = [ 0, 0 ]
                    if ti != -1:
                        texcoords = mesh.texcoords[ti]
                    self.texcoords.append( texcoords )

                    normal = [ 0, 0, 0 ]
                    if ni != -1:
                        normal = mesh.normals[ni]
                    self.normals.append( normal )

                # lookup the mapping and write it out
                self.indices.append( inputIndexToOutputIndex[ pi ] )

    def serialize( self, file ):

        file.write( '#**** Object: %s ****\n' % self.name )
        file.write( 'AttributeBegin\n' );

        file.write( '\tNamedMaterial "%s"\n' % self.material.name )

        file.write( 'Shape "trianglemesh"\n"integer indices"\n[\n' )

        n = int( len( self.indices ) / 3 )
        for i in range(n):
            pi0 = self.indices[ 3 * i ]
            pi1 = self.indices[ 3 * i + 1 ]
            pi2 = self.indices[ 3 * i + 2 ]

            file.write( '\t %d %d %d\n' % ( pi0, pi1, pi2 ) )

        file.write( ']\n' )

        # write positions
        file.write( '"point P"\n[\n' )
        for v in self.positions:
            file.write( '\t %f %f %f\n' % ( v[0], v[1], v[2] ) )
        file.write( ']\n' )

        # write texture coordinates
        file.write( '"float uv"\n[\n' )
        for uv in self.texcoords:
            file.write( '\t %f %f\n' % ( uv[0], uv[1] ) )
        file.write( ']\n' )

        # write texture coordinates
        file.write( '"normal N"\n[\n' )
        for n in self.normals:
            file.write( '\t %f %f %f\n' % ( n[0], n[1], n[2] ) )
        file.write( ']\n' )

        file.write( 'AttributeEnd\n\n\n' )


class Mesh:

    def __init__( self, lines ):

        self.positions = []
        self.normals = []
        self.texcoords = []
        self.groups = { '': Group( '' ) }
        self.materialLibrary = MaterialLibrary()

        currentGroupName = ''
        currentGroup = self.groups[ currentGroupName ]
        currentMaterial = None

        for line in lines:
            lin = line.rstrip()
            if lin == '':
                continue

            tokens = lin.split()

            cmd = tokens[0]
            if cmd == '#':
                continue
            elif cmd == 'v':
                self.positions.append( [ float( p ) for p in tokens[1:] ] )
            elif cmd == 'vn':
                self.normals.append( [ float( p ) for p in tokens[1:] ] )
            elif cmd == 'vt':
                self.texcoords.append( [ float( p ) for p in tokens[1:] ] )
            elif cmd == 'f':
                currentGroup.addFace( Face( tokens ) )
            elif cmd == 'mtllib':
                self.materialLibrary.appendMaterialsFromFile( tokens[1] )
            elif cmd == 'usemtl':
                currentMaterial = self.materialLibrary.getMaterial( tokens[1] )
                currentGroup.setMaterial( currentMaterial )
            elif cmd == 'g':
                currentGroupName = tokens[1]

                if currentGroupName not in self.groups:
                    self.groups[ currentGroupName ] = Group( currentGroupName )

                currentGroup = self.groups[ currentGroupName ]

def saveMeshAsPBRT( mesh, filenamePrefix ):

    f = open( filenamePrefix + "-geom.pbrt", "w" )

    for groupName in mesh.groups.keys():
        group = mesh.groups[ groupName ]
        if len( group.faces ) > 0:
            shape = PBRTShape( mesh, group )
            shape.serialize( f )

    f.close()

def process( file0, file1 ):

    f0 = open( file0 )
    lines0 = f0.readlines()
    f0.close()

    nLines0 = len( lines0 )
    print( 'Read %s: %d lines' % ( file0, nLines0 ) )

    f1 = open( file1 )
    lines1 = f1.readlines()
    f1.close()

    nLines1 = len( lines1 )
    print( 'Read %s: %d lines' % ( file1, nLines1 ) )

    if nLines0 != nLines1:
        print( 'Num lines not equal!' )
        return

f0 = open( "zebra_0.obj" )
lines0 = f0.readlines()
f0.close()

m = Mesh( lines0 )
saveMeshAsPBRT( m, "foo" )
mtllib = PBRTMaterialLibrary( m.materialLibrary )
mtllib.serialize( "foo" )