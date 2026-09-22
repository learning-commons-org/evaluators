from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.academic_subject_enum import AcademicSubjectENUM
from ..models.language_enum import LanguageENUM
from ..types import UNSET, Unset
from typing import cast
import datetime






T = TypeVar("T", bound="LearningComponent")



@_attrs_define
class LearningComponent:
    """ A single, well-defined skill or concept that students are expected to learn

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            description (str | Unset): Description of the specific skill or concept represented
            academic_subject (AcademicSubjectENUM | Unset): Academic subject area
            in_language (LanguageENUM | Unset): Language used in the resource (BCP 47 format)
            date_created (datetime.date | None | Unset): Date created
            date_modified (datetime.date | None | Unset): Date last modified
            examples (list[str] | None | Unset): Examples of how the skill or concept represented might appear in an
                instructional context
     """

    identifier: str
    author: str
    provider: str
    license_: str
    attribution_statement: str
    description: str | Unset = UNSET
    academic_subject: AcademicSubjectENUM | Unset = UNSET
    in_language: LanguageENUM | Unset = UNSET
    date_created: datetime.date | None | Unset = UNSET
    date_modified: datetime.date | None | Unset = UNSET
    examples: list[str] | None | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

        description = self.description

        academic_subject: str | Unset = UNSET
        if not isinstance(self.academic_subject, Unset):
            academic_subject = self.academic_subject.value


        in_language: str | Unset = UNSET
        if not isinstance(self.in_language, Unset):
            in_language = self.in_language.value


        date_created: None | str | Unset
        if isinstance(self.date_created, Unset):
            date_created = UNSET
        elif isinstance(self.date_created, datetime.date):
            date_created = self.date_created.isoformat()
        else:
            date_created = self.date_created

        date_modified: None | str | Unset
        if isinstance(self.date_modified, Unset):
            date_modified = UNSET
        elif isinstance(self.date_modified, datetime.date):
            date_modified = self.date_modified.isoformat()
        else:
            date_modified = self.date_modified

        examples: list[str] | None | Unset
        if isinstance(self.examples, Unset):
            examples = UNSET
        elif isinstance(self.examples, list):
            examples = self.examples


        else:
            examples = self.examples


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
        })
        if description is not UNSET:
            field_dict["description"] = description
        if academic_subject is not UNSET:
            field_dict["academicSubject"] = academic_subject
        if in_language is not UNSET:
            field_dict["inLanguage"] = in_language
        if date_created is not UNSET:
            field_dict["dateCreated"] = date_created
        if date_modified is not UNSET:
            field_dict["dateModified"] = date_modified
        if examples is not UNSET:
            field_dict["examples"] = examples

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

        description = d.pop("description", UNSET)

        _academic_subject = d.pop("academicSubject", UNSET)
        academic_subject: AcademicSubjectENUM | Unset
        if isinstance(_academic_subject,  Unset):
            academic_subject = UNSET
        else:
            academic_subject = AcademicSubjectENUM(_academic_subject)




        _in_language = d.pop("inLanguage", UNSET)
        in_language: LanguageENUM | Unset
        if isinstance(_in_language,  Unset):
            in_language = UNSET
        else:
            in_language = LanguageENUM(_in_language)




        def _parse_date_created(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                date_created_type_0 = datetime.date.fromisoformat(data)



                return date_created_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        date_created = _parse_date_created(d.pop("dateCreated", UNSET))


        def _parse_date_modified(data: object) -> datetime.date | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, str):
                    raise TypeError()
                date_modified_type_0 = datetime.date.fromisoformat(data)



                return date_modified_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(datetime.date | None | Unset, data)

        date_modified = _parse_date_modified(d.pop("dateModified", UNSET))


        def _parse_examples(data: object) -> list[str] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                examples_type_0 = cast(list[str], data)

                return examples_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[str] | None | Unset, data)

        examples = _parse_examples(d.pop("examples", UNSET))


        learning_component = cls(
            identifier=identifier,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            description=description,
            academic_subject=academic_subject,
            in_language=in_language,
            date_created=date_created,
            date_modified=date_modified,
            examples=examples,
        )


        learning_component.additional_properties = d
        return learning_component

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
