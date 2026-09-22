from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.grade_level_enum import GradeLevelENUM
from ..types import UNSET, Unset
from typing import cast
import datetime

if TYPE_CHECKING:
  from ..models.lesson import Lesson





T = TypeVar("T", bound="LessonGrouping")



@_attrs_define
class LessonGrouping:
    """ Set of related lessons within a curriculum; naming and organizational level may vary across curricula (e.g., unit,
    module, chapter, section, theme)

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            group_name (str): Type of grouping (e.g., "unit", "section", "module", "chapter")
            group_level (int): Nesting level of this grouping (0 = top level, 1 = nested once, etc.)
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            name (str | Unset): Name or title of the resource
            ordinal_name (str | Unset): Label with sequence number and descriptive text (e.g., "Unit 1", "Chapter 2")
            position (int | Unset): Position of the resource within its parent
            academic_subject (str | Unset): Academic subject
            grade_level (list[GradeLevelENUM] | Unset):
            in_language (str | Unset): Language used in the resource (BCP 47 format)
            educational_use (str | Unset): Educational use of the resource
            audience (list[str] | Unset): Intended audience of the resource
            curriculum_label (str | Unset): Curriculum-specific categorization of the resource
            lms_loading_guidance (str | Unset): LMS loading guidance for the resource
            is_optional (bool | Unset): Whether the resource is optional to complete
            course_code (str | Unset): Unique identifier for the resource used by the course provider
            publisher_identifier (None | str | Unset): Unique identifier for the resource used by the publisher
            time_required (None | str | Unset): Approximate amount of time required to work through the resource (ISO 8601
                duration format)
            date_created (datetime.date | Unset): Date created
            attribution_statement (str | Unset): Statement that acknowledges the resource's author and provider, as required
                by the CC BY 4.0 license
            lessons (list[Lesson] | Unset): Lessons contained in this resource
     """

    identifier: str
    group_name: str
    group_level: int
    author: str
    provider: str
    license_: str
    name: str | Unset = UNSET
    ordinal_name: str | Unset = UNSET
    position: int | Unset = UNSET
    academic_subject: str | Unset = UNSET
    grade_level: list[GradeLevelENUM] | Unset = UNSET
    in_language: str | Unset = UNSET
    educational_use: str | Unset = UNSET
    audience: list[str] | Unset = UNSET
    curriculum_label: str | Unset = UNSET
    lms_loading_guidance: str | Unset = UNSET
    is_optional: bool | Unset = UNSET
    course_code: str | Unset = UNSET
    publisher_identifier: None | str | Unset = UNSET
    time_required: None | str | Unset = UNSET
    date_created: datetime.date | Unset = UNSET
    attribution_statement: str | Unset = UNSET
    lessons: list[Lesson] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        from ..models.lesson import Lesson # noqa: PLC0415
        identifier = self.identifier

        group_name = self.group_name

        group_level = self.group_level

        author = self.author

        provider = self.provider

        license_ = self.license_

        name = self.name

        ordinal_name = self.ordinal_name

        position = self.position

        academic_subject = self.academic_subject

        grade_level: list[str] | Unset = UNSET
        if not isinstance(self.grade_level, Unset):
            grade_level = []
            for grade_level_item_data in self.grade_level:
                grade_level_item = grade_level_item_data.value
                grade_level.append(grade_level_item)



        in_language = self.in_language

        educational_use = self.educational_use

        audience: list[str] | Unset = UNSET
        if not isinstance(self.audience, Unset):
            audience = self.audience



        curriculum_label = self.curriculum_label

        lms_loading_guidance = self.lms_loading_guidance

        is_optional = self.is_optional

        course_code = self.course_code

        publisher_identifier: None | str | Unset
        if isinstance(self.publisher_identifier, Unset):
            publisher_identifier = UNSET
        else:
            publisher_identifier = self.publisher_identifier

        time_required: None | str | Unset
        if isinstance(self.time_required, Unset):
            time_required = UNSET
        else:
            time_required = self.time_required

        date_created: str | Unset = UNSET
        if not isinstance(self.date_created, Unset):
            date_created = self.date_created.isoformat()

        attribution_statement = self.attribution_statement

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
            "groupName": group_name,
            "groupLevel": group_level,
            "author": author,
            "provider": provider,
            "license": license_,
        })
        if name is not UNSET:
            field_dict["name"] = name
        if ordinal_name is not UNSET:
            field_dict["ordinalName"] = ordinal_name
        if position is not UNSET:
            field_dict["position"] = position
        if academic_subject is not UNSET:
            field_dict["academicSubject"] = academic_subject
        if grade_level is not UNSET:
            field_dict["gradeLevel"] = grade_level
        if in_language is not UNSET:
            field_dict["inLanguage"] = in_language
        if educational_use is not UNSET:
            field_dict["educationalUse"] = educational_use
        if audience is not UNSET:
            field_dict["audience"] = audience
        if curriculum_label is not UNSET:
            field_dict["curriculumLabel"] = curriculum_label
        if lms_loading_guidance is not UNSET:
            field_dict["lmsLoadingGuidance"] = lms_loading_guidance
        if is_optional is not UNSET:
            field_dict["isOptional"] = is_optional
        if course_code is not UNSET:
            field_dict["courseCode"] = course_code
        if publisher_identifier is not UNSET:
            field_dict["publisherIdentifier"] = publisher_identifier
        if time_required is not UNSET:
            field_dict["timeRequired"] = time_required
        if date_created is not UNSET:
            field_dict["dateCreated"] = date_created
        if attribution_statement is not UNSET:
            field_dict["attributionStatement"] = attribution_statement
        if lessons is not UNSET:
            field_dict["lessons"] = lessons

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        from ..models.lesson import Lesson # noqa: PLC0415
        d = dict(src_dict)
        identifier = d.pop("identifier")

        group_name = d.pop("groupName")

        group_level = d.pop("groupLevel")

        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        name = d.pop("name", UNSET)

        ordinal_name = d.pop("ordinalName", UNSET)

        position = d.pop("position", UNSET)

        academic_subject = d.pop("academicSubject", UNSET)

        _grade_level = d.pop("gradeLevel", UNSET)
        grade_level: list[GradeLevelENUM] | Unset = UNSET
        if _grade_level is not UNSET:
            grade_level = []
            for grade_level_item_data in _grade_level:
                grade_level_item = GradeLevelENUM(grade_level_item_data)



                grade_level.append(grade_level_item)


        in_language = d.pop("inLanguage", UNSET)

        educational_use = d.pop("educationalUse", UNSET)

        audience = cast(list[str], d.pop("audience", UNSET))


        curriculum_label = d.pop("curriculumLabel", UNSET)

        lms_loading_guidance = d.pop("lmsLoadingGuidance", UNSET)

        is_optional = d.pop("isOptional", UNSET)

        course_code = d.pop("courseCode", UNSET)

        def _parse_publisher_identifier(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        publisher_identifier = _parse_publisher_identifier(d.pop("publisherIdentifier", UNSET))


        def _parse_time_required(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        time_required = _parse_time_required(d.pop("timeRequired", UNSET))


        _date_created = d.pop("dateCreated", UNSET)
        date_created: datetime.date | Unset
        if isinstance(_date_created,  Unset):
            date_created = UNSET
        else:
            date_created = datetime.date.fromisoformat(_date_created)




        attribution_statement = d.pop("attributionStatement", UNSET)

        _lessons = d.pop("lessons", UNSET)
        lessons: list[Lesson] | Unset = UNSET
        if _lessons is not UNSET:
            lessons = []
            for lessons_item_data in _lessons:
                lessons_item = Lesson.from_dict(lessons_item_data)



                lessons.append(lessons_item)


        lesson_grouping = cls(
            identifier=identifier,
            group_name=group_name,
            group_level=group_level,
            author=author,
            provider=provider,
            license_=license_,
            name=name,
            ordinal_name=ordinal_name,
            position=position,
            academic_subject=academic_subject,
            grade_level=grade_level,
            in_language=in_language,
            educational_use=educational_use,
            audience=audience,
            curriculum_label=curriculum_label,
            lms_loading_guidance=lms_loading_guidance,
            is_optional=is_optional,
            course_code=course_code,
            publisher_identifier=publisher_identifier,
            time_required=time_required,
            date_created=date_created,
            attribution_statement=attribution_statement,
            lessons=lessons,
        )


        lesson_grouping.additional_properties = d
        return lesson_grouping

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
