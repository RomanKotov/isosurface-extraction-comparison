import numpy as np
from abc import ABC, abstractmethod
import json
from typing import Tuple, Self, TypedDict

type Array1D = np.ndarray[Tuple[int], np.float64]
type Array3D = np.ndarray[Tuple[int, int, int], np.float64]
type Point3D = Tuple[float, float, float]


class RFunctionInfo(TypedDict):
    title: str
    params: dict
    children: list[Self] | None


class AbstractRF(ABC):
    @abstractmethod
    def compute(self, x: Array1D, y: Array1D, z: Array1D) -> Array1D:
        pass

    @abstractmethod
    def to_dict(self) -> RFunctionInfo:
        pass

    def __str__(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def __invert__(self) -> Self:
        return Negate(self)

    def __and__(self, other: Self) -> Self:
        return And(self, other)

    def __or__(self, other: Self) -> Self:
        return Or(self, other)

    def __sub__(self, other: Self) -> Self:
        return Sub(self, other)

    @staticmethod
    def _and(f1: Array1D, f2: Array1D) -> Array1D:
        return f1 + f2 - np.sqrt(f1**2 + f2**2)

    @staticmethod
    def _or(f1: Array1D, f2: Array1D) -> Array1D:
        return f1 + f2 + np.sqrt(f1**2 + f2**2)

    @staticmethod
    def _not(f: Array1D) -> Array1D:
        return -f

    @classmethod
    def _sub(cls, f1: Array1D, f2: Array1D) -> Array1D:
        return cls._and(f1, cls._not(f2))


class AbstractBinaryRF(AbstractRF):
    def __init__(self, f1: AbstractRF, f2: AbstractRF, operation: str):
        self.f1 = f1
        self.f2 = f2
        self.operation = operation

    def to_dict(self):
        return RFunctionInfo(
            title=f"Binary Operation ({self.operation})",
            children=[self.f1.to_dict(), self.f2.to_dict()]
        )


class Negate(AbstractRF):
    def __init__(self, fn: AbstractRF):
        self.fn = fn

    def compute(self, x, y, z):
        return -(self.fn.compute(x, y, z))

    def to_dict(self):
        return RFunctionInfo(
            title="Negate",
            children=[self.fn.to_dict()]
        )


class And(AbstractBinaryRF):
    def __init__(self, f1: AbstractBinaryRF, f2: AbstractBinaryRF):
        super().__init__(f1, f2, "AND")

    def compute(self, x, y, z):
        f1 = self.f1.compute(x, y, z)
        f2 = self.f2.compute(x, y, z)
        return self._and(f1, f2)


class Or(AbstractBinaryRF):
    def __init__(self, f1: AbstractBinaryRF, f2: AbstractBinaryRF):
        super().__init__(f1, f2, "OR")

    def compute(self, x, y, z):
        f1 = self.f1.compute(x, y, z)
        f2 = self.f2.compute(x, y, z)
        return self._or(f1, f2)


class Sub(AbstractBinaryRF):
    def __init__(self, f1: AbstractBinaryRF, f2: AbstractBinaryRF):
        super().__init__(f1, f2, "-")

    def compute(self, x, y, z):
        f1 = self.f1.compute(x, y, z)
        f2 = self.f2.compute(x, y, z)
        return self._sub(f1, f2)


class Sphere(AbstractRF):
    def __init__(
            self,
            center: Point3D = (0, 0, 0),
            radius: float = 1.0,
    ):
        self.radius = radius
        self.center = center

    def to_dict(self):
        return RFunctionInfo(
            title="Sphere",
            params={
                "center": self.center,
                "radius": self.radius,
            }
        )

    def compute(self, x, y, z):
        cx, cy, cz = self.center
        return self.radius**2 - (
            (self.x-cx)**2 +
            (self.y-cy)**2 +
            (self.z-cz)**2
        )


class Box(AbstractRF):
    def __init__(
            self,
            center: Point3D = (0, 0, 0),
            size: Point3D = (1.0, 1.0, 1.0),
    ):
        self.size = size
        self.center = center

    def to_dict(self):
        return RFunctionInfo(
            title="Box",
            params={
                "center": self.center,
                "size": self.size
            }
        )

    def compute(self, x, y, z):
        cx, cy, cz = self.center
        sx, sy, sz = self.size
        f_x = sx - np.abs(x - cx)
        f_y = sy - np.abs(y - cy)
        f_z = sz - np.abs(z - cz)
        return self._and(self._and(f_x, f_y), f_z)


class CylinderZ(AbstractRF):
    def __init__(
            self,
            center: Point3D = (0, 0, 0),
            radius: float = 1.0,
            height: float = 2.0

    ):
        self.center = center
        self.radius = radius
        self.height = height

    def to_dict(self):
        return RFunctionInfo(
            title="CylinderZ",
            params={
                "center": self.center,
                "radius": self.radius,
                "height": self.height
            }
        )

    def compute(self, x, y, z):
        cx, cy, cz = self.center
        f_circle = self.radius**2 - ((x - cx)**2 + (y - cy)**2)
        f_height = self.height/2 - np.abs(z - cz)
        return self._and(f_circle, f_height)


class Torus(AbstractRF):
    def __init__(
            self,
            center: Point3D = (0, 0, 0),
            r_major: float = 2.0,
            r_minor: float = 0.5

    ):
        self.center = center
        self.r_major = r_major
        self.r_minor = r_minor

    def to_dict(self):
        return RFunctionInfo(
            title="Tours",
            params={
                "center": self.center,
                "r_major": self.r_major,
                "r_minor": self.r_minor
            }
        )

    def compute(self, x, y, z):
        cx, cy, cz = self.center
        d_xy = np.sqrt((x - cx)**2 + (y - cy)**2)
        return self.r_minor**2 - (d_xy - self.r_major)**2 - (z - cz)**2
