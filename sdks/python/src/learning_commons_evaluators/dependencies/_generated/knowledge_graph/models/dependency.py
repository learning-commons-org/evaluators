from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.dependency_target import DependencyTarget





T = TypeVar("T", bound="Dependency")



@_attrs_define
class Dependency:
    """ Lesson grouping and the other lesson groupings it depends on (prerequisites).

        Attributes:
            source (str): Unique identifier for the resource in Knowledge Graph
            has_dependency (list[DependencyTarget]): Lesson groupings that this source has a dependency on (prerequisites)
            source_name (str | Unset): Name or title of the resource
            source_curriculum_label (str | Unset): Curriculum label of the source lesson grouping (e.g., "Unit", "Section")
     """

    source: str
    has_dependency: list[DependencyTarget]
    source_name: str | Unset = UNSET
    source_curriculum_label: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.dependency_target import DependencyTarget # noqa: PLC0415
        source = self.source

        has_dependency = []
        for has_dependency_item_data in self.has_dependency:
            has_dependency_item = has_dependency_item_data.to_dict()
            has_dependency.append(has_dependency_item)



        source_name = self.source_name

        source_curriculum_label = self.source_curriculum_label


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "source": source,
            "hasDependency": has_dependency,
        })
        if source_name is not UNSET:
            field_dict["sourceName"] = source_name
        if source_curriculum_label is not UNSET:
            field_dict["sourceCurriculumLabel"] = source_curriculum_label

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.dependency_target import DependencyTarget # noqa: PLC0415
        d = dict(src_dict)
        source = d.pop("source")

        has_dependency = []
        _has_dependency = d.pop("hasDependency")
        for has_dependency_item_data in (_has_dependency):
            has_dependency_item = DependencyTarget.from_dict(has_dependency_item_data)



            has_dependency.append(has_dependency_item)


        source_name = d.pop("sourceName", UNSET)

        source_curriculum_label = d.pop("sourceCurriculumLabel", UNSET)

        dependency = cls(
            source=source,
            has_dependency=has_dependency,
            source_name=source_name,
            source_curriculum_label=source_curriculum_label,
        )


        dependency.additional_properties = d
        return dependency

    @property
    def additional_keys(self) -> list[str]:
        return list(self.additional_properties.keys())

    def __getitem__(self, key: str) -> Any:
        return self.additional_properties[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.additional_properties[key] = value

    def __delitem__(self, key: str) -> None:
        del self.additional_properties[key]

    def __contains__(self, key: str) -> bool:
        return key in self.additional_properties
