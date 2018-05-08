import sys
from os import listdir, remove, rename
from os.path import isfile, join,expandvars
import PIL
from PIL import Image
import os

# This script generates low resolution of all PBR textures
# High resolution textures are only used in Best mode

root = os.path.expandvars('$HBP/Models')

# First remove all low res versions

print "Clean low resolution textures"

for path, subdirs, files in os.walk(root):
    for filename in files:
        file,ext = os.path.splitext(filename)
        if ((ext=='.png' or ext=='.jpg') and
            (filename.find('LOWPBRFULL_')==0 or filename.find('LOWPBR_')==0 or filename.find('_Height')==0
            or filename.find('LOWSKY_')==0)):
                remove(os.path.join(path, filename))

# Generate low resolution versions of PBR

print "Generate low resolution textures"

for path, subdirs, files in os.walk(root):
    for filename in files:
        file,ext = os.path.splitext(filename)
        if ((ext=='.png' or ext=='.jpg') and
            (filename.find('PBRFULL_')==0 or filename.find('PBR_')==0)):
                im = Image.open(os.path.join(path, filename))
                if im.size[0]>1 and im.size[1]>1:
                    if filename.find('_Normal')==-1:
                        filter = PIL.Image.NEAREST
                    else:
                        filter = PIL.Image.LANCZOS
                    neww = im.size[0]/2
                    newh = im.size[1]/2

                    maxsize = neww

                    if filename.find('Mixed_AO')!=-1:
                        maxsize = 256
                    elif filename.find('_Metallic')!=-1:
                        maxsize = 512
                    elif filename.find('_Roughness')!=-1:
                        maxsize = 512

                    if neww>maxsize:
                        neww = maxsize
                    if newh>maxsize:
                        newh = maxsize

                    im = im.resize((neww,newh),filter)

                im.save(os.path.join(path,'LOW')+filename)


# Generate low resolution versions of sky env. map

print "Generate low resolution of sky textures"

root = os.path.expandvars('$HBP/Models/sky')
for path, subdirs, files in os.walk(root):
    for filename in files:
        file,ext = os.path.splitext(filename)
        if ((ext=='.png' or ext=='.jpg')):

                im = Image.open(os.path.join(path, filename))
                filter = PIL.Image.LANCZOS

                neww = im.size[0]/2
                newh = im.size[1]/2

                im = im.resize((neww,newh),filter)
                im.save(os.path.join(path,'LOWSKY_')+filename, quality=95)

