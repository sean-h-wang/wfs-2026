from __future__ import annotations
from dataclasses import dataclass
import math

__all__ = ["Point"]

@dataclass
class Point:
    
    def __init__(self, x, z, relative: "Point" = None):
        if relative is not None:
            self.x = x + relative.x
            self.y = -1
            self.z = z + relative.z
        else:
            self.x = x
            self.y = -1
            self.z = z
    
    def __str__(self):
        return f"({self.x} {self.y} {self.z})"
    
    def __add__(self, other: "Point"):
        return Point(self.x + other.x, self.y + other.y, self.z + other.z)
    
    def __radd__(self, other: "Point"):
        return self.__add__(other)
    
    def reflect_xz(self):
        p2 = Point(self.x, self.z)
        p2.y = -self.y
        return p2

@dataclass
class Point2:
    
    def __init__(self, x, z, relative: "Point2" = None):
        theta = math.radians(1)
        
        # z and self.proj_z are the user input
        if relative is not None:
            self.x = x + relative.x
            self.proj_z = z + relative.proj_z
        else:
            self.x = x
            self.proj_z = z
        
        # Computed coordinates for OpenFOAM
        self.y = self.proj_z * math.sin(theta)
        self.z = self.proj_z * math.cos(theta)  # actual openfoam z
    
    def __str__(self):
        return f"({self.x} {self.y} {self.z})"
    
    def __add__(self, other: "Point2"):
        # Adds the proj_z values and creates a third point
        return Point2(self.x + other.x, self.proj_z + other.proj_z)
    
    def __radd__(self, other: "Point2"):
        return self.__add__(other)
    
    def reflect_xz(self):
        # Reflecting across xz flips the sign of proj_z
        return Point2(self.x, -self.proj_z)