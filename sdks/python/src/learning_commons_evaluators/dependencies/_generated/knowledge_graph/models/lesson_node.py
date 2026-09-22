from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset






T = TypeVar("T", bound="LessonNode")



@_attrs_define
class LessonNode:
    """ Lesson node in the course hierarchy for summary view (minimal fields)

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            name (str): Name or title of the resource
            position (int): Position of the resource within its parent
            ordinal_name (str | Unset): Label with sequence number and descriptive text (e.g., "Lesson 1")
     """

    identifier: str
    name: str
    position: int
    ordinal_name: str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        name = self.name

        position = self.position

        ordinal_name = self.ordinal_name


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "name": name,
            "position": position,
        })
        if ordinal_name is not UNSET:
            field_dict["ordinalName"] = ordinal_name

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        name = d.pop("name")

        position = d.pop("position")

        ordinal_name = d.pop("ordinalName", UNSET)

        lesson_node = cls(
            identifier=identifier,
            name=name,
            position=position,
            ordinal_name=ordinal_name,
        )


        lesson_node.additional_properties = d
        return lesson_node

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
