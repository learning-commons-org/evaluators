from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset






T = TypeVar("T", bound="DependencyTarget")



@_attrs_define
class DependencyTarget:
    """ Lesson grouping that is depended upon (a prerequisite).

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            name (str | Unset): Name or title of the resource
            curriculum_label (str | Unset): Curriculum label of the target lesson grouping (e.g., "Unit", "Section")
     """

    identifier: str
    name: str | Unset = UNSET
    curriculum_label: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        name = self.name

        curriculum_label = self.curriculum_label


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
        })
        if name is not UNSET:
            field_dict["name"] = name
        if curriculum_label is not UNSET:
            field_dict["curriculumLabel"] = curriculum_label

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        name = d.pop("name", UNSET)

        curriculum_label = d.pop("curriculumLabel", UNSET)

        dependency_target = cls(
            identifier=identifier,
            name=name,
            curriculum_label=curriculum_label,
        )


        dependency_target.additional_properties = d
        return dependency_target

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
