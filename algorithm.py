import time
from abc import ABC, abstractmethod
from dataclasses import dataclass

from .r import AbstractRF, Array1D, Array3D


@dataclass
class Mesh:
    vertices: Array3D
    faces: Array3D


@dataclass
class HistoryItem:
    title: str
    mesh: Mesh


@dataclass
class FitMeta:
    elapsed_time_seconds: float


class AbstractAlgorithm(ABC):
    def __init__(self, r_function: AbstractRF, options: dict):
        self.options = options
        self.history: list[HistoryItem] = []

    def __str__(self):
        return f"{self.__class__.__name__}({self.options})"

    @abstractmethod
    def _do_fit(self, x: Array1D, y: Array1D, z: Array1D) -> Mesh:
        raise NotImplementedError("Unable to fit this algorithm")

    def fit(self, x: Array1D, y: Array1D, z: Array1D):
        self._meta = FitMeta()
        self.history: list[HistoryItem] = []
        start = time.perf_counter()
        self._mesh = self._do_fit(x, y, z)
        end = time.perf_counter()
        self._meta.elapsed_time_seconds = end - start

    def history_items(self):
        return self.history

    def get_mesh(self):
        return self._mesh

    def _add_history_item(self, item: HistoryItem):
        self.history.append(item)
