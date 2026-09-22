from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast

if TYPE_CHECKING:
  from ..models.lesson_node import LessonNode





T = TypeVar("T", bound="LessonGroupingNode")



@_attrs_define
class LessonGroupingNode:
    """ Lesson grouping node in the course hierarchy for summary view (minimal fields)

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            name (str): Name or title of the resource
            group_name (str): Type of grouping (e.g., "unit", "section", "module", "chapter")
            group_level (int): Nesting level of this grouping (0 = top level, 1 = nested once, etc.)
            position (int): Position of the resource within its parent
            ordinal_name (str | Unset): Label with sequence number and descriptive text (e.g., "Unit 1", "Chapter 2")
            children (list[LessonGroupingNode] | Unset): Nested lesson groupings within this grouping
            lessons (list[LessonNode] | Unset): Lessons within this grouping
     """

    identifier: str
    name: str
    group_name: str
    group_level: int
    position: int
    ordinal_name: str | Unset = UNSET
    children: list[LessonGroupingNode] | Unset = UNSET
    lessons: list[LessonNode] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.lesson_node import LessonNode # noqa: PLC0415
        identifier = self.identifier

        name = self.name

        group_name = self.group_name

        group_level = self.group_level

        position = self.position

        ordinal_name = self.ordinal_name

        children: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.children, Unset):
            children = []
            for children_item_data in self.children:
                children_item = children_item_data.to_dict()
                children.append(children_item)



        lessons: list[dict[str, Any]] | Unset = UNSET
        if not isinstance(self.lessons, Unset):
            lessons = []
            for lessons_item_data in self.lessons:
                lessons_item = lessons_item_data.to_dict()
                lessons.append(lessons_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "name": name,
            "groupName": group_name,
            "groupLevel": group_level,
            "position": position,
        })
        if ordinal_name is not UNSET:
            field_dict["ordinalName"] = ordinal_name
        if children is not UNSET:
            field_dict["children"] = children
        if lessons is not UNSET:
            field_dict["lessons"] = lessons

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lesson_node import LessonNode # noqa: PLC0415
        d = dict(src_dict)
        identifier = d.pop("identifier")

        name = d.pop("name")

        group_name = d.pop("groupName")

        group_level = d.pop("groupLevel")

        position = d.pop("position")

        ordinal_name = d.pop("ordinalName", UNSET)

        _children = d.pop("children", UNSET)
        children: list[LessonGroupingNode] | Unset = UNSET
        if _children is not UNSET:
            children = []
            for children_item_data in _children:
                children_item = LessonGroupingNode.from_dict(children_item_data)



                children.append(children_item)


        _lessons = d.pop("lessons", UNSET)
        lessons: list[LessonNode] | Unset = UNSET
        if _lessons is not UNSET:
            lessons = []
            for lessons_item_data in _lessons:
                lessons_item = LessonNode.from_dict(lessons_item_data)



                lessons.append(lessons_item)


        lesson_grouping_node = cls(
            identifier=identifier,
            name=name,
            group_name=group_name,
            group_level=group_level,
            position=position,
            ordinal_name=ordinal_name,
            children=children,
            lessons=lessons,
        )


        lesson_grouping_node.additional_properties = d
        return lesson_grouping_node

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
