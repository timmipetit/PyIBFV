#! /usr/bin/env python

import OpenGL 
OpenGL.ERROR_ON_COPY = True 
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from OpenGL.GL.framebufferobjects import *
from OpenGL.arrays import vbo

import time
import sys
import math
import random
import numpy as np
from PIL import Image

class PyIBFV:
    
    def __init__(self):
        self.nmesh = 100
        self.pattern_res = 64
        self.num_patterns = 32
        self.alpha = 0.12
        self.textures = []
        self.scale = 4.0
        self.tmax = 512/(self.scale*self.pattern_res)
        self.dmax = self.scale / 512
        
        self.last_time = time.time()
        self.frames = 0
        self.sa = 0.01
     
    def InitGL(self, Width, Height):             
        glClearColor(0.0, 0.0, 0.0, 0.0)  
        glClearDepth(1.0)                   
        glShadeModel(GL_SMOOTH)             
     
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()                   

        gluPerspective(45.0, float(Width)/float(Height), 0.1, 100.0)
     
        glMatrixMode(GL_MODELVIEW)
        
        # Create fbo with 2 textures.
        self.fbo = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo )

        # FBO texture 1
        self.renderedTexture1 = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.renderedTexture1)
        glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, 512, 512, 0,GL_RGB, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        
        # FBO texture 2
        self.renderedTexture2 = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.renderedTexture2)
        glTexImage2D(GL_TEXTURE_2D, 0,GL_RGB, 512, 512, 0,GL_RGB, GL_UNSIGNED_BYTE, None)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        
        # Set the first texture as color attachment
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, self.renderedTexture1, 0)

        # Set the list of draw buffers.
        glDrawBuffers(1, GL_COLOR_ATTACHMENT0) #"1" is the size of DrawBuffers
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        # Clear the 2nd texture
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, self.renderedTexture2, 0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        self.framenr = 0
        
        # Set the blending function
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        
        # init VBO's for for mesh location and texture coordinates
        # based on: http://dan.lecocq.us/wordpress/2009/12/25/triangle-strip-for-grids-a-construction/
        self.DM = 1.0 / (self.nmesh-1.0)
        size = self.nmesh ** 2 * 2
        
        # locations
        locations = self.getDisplacements()
        self.vbo_locations = vbo.VBO(locations)
                
        # texture coordinates
        coords = np.empty(size, dtype=np.float32)
        index = 0
        for i in range(self.nmesh):
            x = self.DM*i
            for j in range(self.nmesh):
                y = self.DM*j
                coords[index + 0] = x
                coords[index + 1] = y
                index += 2
        self.vbo_coords = vbo.VBO(coords)

                
        # indices
        self.num_indices = self.nmesh * (self.nmesh - 1) * 2
        indices = np.empty(self.num_indices, dtype=np.uint16)
        index = 0
        i = 0
        for x in range(self.nmesh - 1):
            for y in range(self.nmesh):
                if x % 2 == 0:
                    indices[i+0] = index + 0
                    indices[i+1] = index + self.nmesh
                    index += 1 
                    i += 2
                else:
                    indices[i+0] = index + 0
                    indices[i+1] = index + self.nmesh
                    index -= 1
                    i += 2
            index = indices[i-1]
        self.ibo = vbo.VBO(indices, GL_DYNAMIC_DRAW, GL_ELEMENT_ARRAY_BUFFER)
        
    def getDisplacements(self):
        size = self.nmesh ** 2 * 2
        locations = np.empty(size, dtype=np.float32)
        index = 0
        for i in range(self.nmesh):
            x = self.DM*i
            for j in range(self.nmesh):
                y = self.DM*j
                [px, py] = self.getDisplacement(x, y)
                locations[index + 0] = px
                locations[index + 1] = py
                index += 2
        return locations
        
    def updateDisplacements(self):
        self.sa = 0.010*math.cos(self.framenr*2.0*math.pi/200.0)
        self.vbo_locations.set_array(self.getDisplacements())
     
    # The function called when our window is resized (which shouldn't happen if you enable fullscreen, below)
    def ReSizeGLScene(self, Width, Height):
        if Height == 0:                        # Prevent A Divide By Zero If The Window Is Too Small 
            Height = 1
     
        glViewport(0, 0, Width, Height)        # Reset The Current Viewport And Perspective Transformation
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, float(Width)/float(Height), 0.1, 100.0)
        glMatrixMode(GL_MODELVIEW)
        
    def makePatterns(self):
        lut = np.empty(256)
        phase = np.empty((self.pattern_res,self.pattern_res), dtype=int)
        pat = np.empty((self.pattern_res,self.pattern_res, 4), dtype=np.uint8)

        for i in range(256): 
            lut[i] = 0 if i < 127 else 255
        
        for i in range(self.pattern_res):
            for j in range(self.pattern_res):
                phase[i][j] = random.randint(0, 255)
                
        for k in range(self.num_patterns):
            t = k*256/self.num_patterns
            for i in range(self.pattern_res):
                for j in range(self.pattern_res):
                    val = lut[(t + phase[i][j]) % 255]
                    pat[i][j][0] = pat[i][j][1] = pat[i][j][2] = val
                    pat[i][j][3] = int(self.alpha * 255)
            texture = glGenTextures(1)
            
            glBindTexture(GL_TEXTURE_2D, texture)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
            glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
            glTexEnvf(GL_TEXTURE_ENV, GL_TEXTURE_ENV_MODE, GL_REPLACE)
            glTexImage2D(GL_TEXTURE_2D, 0, 4, self.pattern_res, self.pattern_res, 0, GL_RGBA, GL_UNSIGNED_BYTE, pat)
            #self.saveTexture((self.pattern_res, self.pattern_res), "screenshots/pattern_%d.png" % k)
            glBindTexture(GL_TEXTURE_2D, 0)
            
            self.textures.append(texture)
        
        
        
    def getDisplacement(self, x, y):
        dx = x - 0.5        
        dy = y - 0.5
        r  = dx*dx + dy*dy
        if r < 0.0001:
            r = 0.0001
        vx = self.sa*dx/r + 0.02 
        vy = self.sa*dy/r
        r  = vx*vx + vy*vy
        if r > self.dmax ** 2:
          r  = math.sqrt(r)
          vx *= self.dmax/r
          vy *= self.dmax/r
        px = x + vx    
        py = y + vy
        return [px, py]
     
    # The main drawing function. 
    def DrawGLScene(self):  
        # update displacements vbo
        self.updateDisplacements()
        
        # Draw to the texture in the FBO
        glBindFramebuffer(GL_FRAMEBUFFER, self.fbo)
        glViewport(0,0,512,512)
        # pingpong between the 2 FBO textures
        glFramebufferTexture(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, self.renderedTexture2 if self.framenr % 2 is 0 else self.renderedTexture1, 0)
        
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()             
        glTranslatef(-1.0, -1.0, 0.0)
        glScalef(2.0, 2.0, 1.0)
        
        # bind the other FBO texture, so that we can warp it
        DM = 1.0 / (self.nmesh-1.0)
        texture = self.framenr % self.num_patterns
        glEnable(GL_TEXTURE_2D) 
        glBindTexture(GL_TEXTURE_2D, self.renderedTexture2 if self.framenr % 2 is not 0  else self.renderedTexture1)
        
        # warp the texture!
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_TEXTURE_COORD_ARRAY)
           
        self.vbo_locations.bind()
        glVertexPointer(2, GL_FLOAT, 0, self.vbo_locations) 
        self.vbo_coords.bind()
        glTexCoordPointer(2, GL_FLOAT, 0, self.vbo_coords)
        
        self.ibo.bind()
        # remember that the last param should be None, not 0!
        glDrawElements(GL_TRIANGLE_STRIP, self.num_indices, GL_UNSIGNED_SHORT, None)
        
        self.ibo.unbind()
        self.vbo_locations.unbind()
        self.vbo_coords.unbind()
        
        glDisableClientState(GL_TEXTURE_COORD_ARRAY)
        glDisableClientState(GL_VERTEX_ARRAY)
        
        # Blend in some "fresh" noise    
        glEnable(GL_BLEND)
        glBindTexture(GL_TEXTURE_2D, self.textures[texture])
        glBegin(GL_QUAD_STRIP)
        glTexCoord2f(0.0,  0.0)  
        glVertex2f(0.0, 0.0)
        glTexCoord2f(0.0,  self.tmax)
        glVertex2f(0.0, 1.0)
        glTexCoord2f(self.tmax, 0.0)   
        glVertex2f(1.0, 0.0)
        glTexCoord2f(self.tmax, self.tmax)   
        glVertex2f(1.0, 1.0)
        glEnd();
        glDisable(GL_BLEND);
        

        # Draw texture to the screen
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glViewport(0,0,512,512)
        
        glLoadIdentity()                 
        glTranslatef(-1.0, -1.0, 0.0)
        glScalef(2.0, 2.0, 1.0)
	    
        glBindTexture(GL_TEXTURE_2D, self.renderedTexture2 if self.framenr % 2 is 0  else self.renderedTexture1)
        #self.saveTexture((512, 512), "screenshots/%d.png" % self.framenr)
        
        glBegin(GL_QUAD_STRIP)
        glTexCoord2f(0.0,  0.0)  
        glVertex2f(0.0, 0.0)
        glTexCoord2f(0.0,  1.0)
        glVertex2f(0.0, 1.0)
        glTexCoord2f(1.0, 0.0)   
        glVertex2f(1.0, 0.0)
        glTexCoord2f(1.0, 1.0)   
        glVertex2f(1.0, 1.0)
        glEnd()
        glDisable(GL_TEXTURE_2D)
        
        glutSwapBuffers()
        self.framenr += 1
        self.fps()
        #time.sleep(0.01)
        
    def saveTexture(self, size, filename):
        tex = np.empty(size[0] * size[1], dtype=np.uint8)
        string = glGetTexImage(GL_TEXTURE_2D, 0, GL_LUMINANCE, GL_UNSIGNED_BYTE, tex)
        imm = Image.fromstring("L", size, string)
        imm.save(filename)
        
    def fps(self):
        self.frames += 1
        if time.time() - self.last_time >= 5:
            current_fps = self.frames / (time.time() - self.last_time)
            print '%.2f fps' % current_fps
            self.frames = 0
            self.last_time = time.time()     
            
    def keyPressed(self, *args):
        # escape
	    if args[0] == '\x1b':
		    sys.exit()
     
    def main(self):
        glutInit(sys.argv)
        glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE | GLUT_DEPTH)
        glutInitWindowSize(512, 512)
        glutInitWindowPosition(0, 0)
        window = glutCreateWindow("PyIBFV")
        glutDisplayFunc(self.DrawGLScene)
        glutIdleFunc(self.DrawGLScene)
        glutReshapeFunc(self.ReSizeGLScene)
        glutKeyboardFunc(self.keyPressed)
        self.InitGL(512, 512)
        falloffValue = 1.0
        self.rotY = 0.0
        
        self.makePatterns()
        glutMainLoop()
 
 
if __name__ == "__main__":
	print "Hit ESC key to quit."
	ibfv = PyIBFV()
	ibfv.main()
	main()
