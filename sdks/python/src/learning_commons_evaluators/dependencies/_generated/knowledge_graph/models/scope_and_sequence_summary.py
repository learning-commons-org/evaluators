from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.scope_and_sequence_summary_view import ScopeAndSequenceSummaryView
from typing import cast

if TYPE_CHECKING:
  from ..models.lesson_grouping_node import LessonGroupingNode





T = TypeVar("T", bound="ScopeAndSequenceSummary")



@_attrs_define
class ScopeAndSequenceSummary:
    """ Hierarchical structure of a course showing lesson groupings and lessons (`summary` view)

        Attributes:
            course_id (str): Unique identifier for the resource in Knowledge Graph
            course_name (str): Name or title of the resource
            view (ScopeAndSequenceSummaryView): Level of detail included in the response
            lesson_groupings (list[LessonGroupingNode]): Top-level lesson groupings (e.g., units, modules, chapters)
     """

    course_id: str
    course_name: str
    view: ScopeAndSequenceSummaryView
    lesson_groupings: list[LessonGroupingNode]
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.lesson_grouping_node import LessonGroupingNode # noqa: PLC0415
        course_id = self.course_id

        course_name = self.course_name

        view = self.view.value

        lesson_groupings = []
        for lesson_groupings_item_data in self.lesson_groupings:
            lesson_groupings_item = lesson_groupings_item_data.to_dict()
            lesson_groupings.append(lesson_groupings_item)




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "courseId": course_id,
            "courseName": course_name,
            "view": view,
            "lessonGroupings": lesson_groupings,
        })

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lesson_grouping_node import LessonGroupingNode # noqa: PLC0415
        d = dict(src_dict)
        course_id = d.pop("courseId")

        course_name = d.pop("courseName")

        view = ScopeAndSequenceSummaryView(d.pop("view"))




        lesson_groupings = []
        _lesson_groupings = d.pop("lessonGroupings")
        for lesson_groupings_item_data in (_lesson_groupings):
            lesson_groupings_item = LessonGroupingNode.from_dict(lesson_groupings_item_data)



            lesson_groupings.append(lesson_groupings_item)


        scope_and_sequence_summary = cls(
            course_id=course_id,
            course_name=course_name,
            view=view,
            lesson_groupings=lesson_groupings,
        )


        scope_and_sequence_summary.additional_properties = d
        return scope_and_sequence_summary

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
