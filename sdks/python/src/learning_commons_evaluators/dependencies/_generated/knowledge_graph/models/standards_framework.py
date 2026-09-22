from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.academic_subject_enum import AcademicSubjectENUM
from ..models.adoption_status_enum import AdoptionStatusENUM
from ..models.jurisdiction_enum import JurisdictionENUM
from ..models.language_enum import LanguageENUM
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="StandardsFramework")



@_attrs_define
class StandardsFramework:
    """ Represents a complete academic standards document published by an official body like a state department of
    education.

    StandardsFramework serves as the root entity that organizes and contextualizes all standards within a given
    standards framework. Each standards framework represents a complete standards document with its own jurisdiction,
    subject area, and adoption status.

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            case_identifier_uuid (UUID): CASE Network UUID for the resource
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            is_current (bool): Whether this framework is the currently adopted version. When false, the framework has been
                superseded but is retained. The framework list returns current frameworks by default; pass
                includeNonCurrent=true to include all frameworks.
            case_identifier_uri (str | Unset): URI referencing the CASE Network equivalent
            name (None | str | Unset): Name or title of the resource
            description (None | str | Unset): Description with additional context
            jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
            academic_subject (AcademicSubjectENUM | Unset): Academic subject area
            in_language (LanguageENUM | Unset): Language used in the resource (BCP 47 format)
            adoption_status (AdoptionStatusENUM | Unset): Adoption status of a standards framework
            date_modified (datetime.date | None | Unset): Date last modified
            notes (None | str | Unset): (Optional) Additional context, commentary, clarifications, or usage guidance
     """

    identifier: str
    case_identifier_uuid: UUID
    author: str
    provider: str
    license_: str
    attribution_statement: str
    is_current: bool
    case_identifier_uri: str | Unset = UNSET
    name: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    jurisdiction: JurisdictionENUM | Unset = UNSET
    academic_subject: AcademicSubjectENUM | Unset = UNSET
    in_language: LanguageENUM | Unset = UNSET
    adoption_status: AdoptionStatusENUM | Unset = UNSET
    date_modified: datetime.date | None | Unset = UNSET
    notes: None | str | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        case_identifier_uuid = str(self.case_identifier_uuid)

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

        is_current = self.is_current

        case_identifier_uri = self.case_identifier_uri

        name: None | str | Unset
        if isinstance(self.name, Unset):
            name = UNSET
        else:
            name = self.name

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        jurisdiction: str | Unset = UNSET
        if not isinstance(self.jurisdiction, Unset):
            jurisdiction = self.jurisdiction.value


        academic_subject: str | Unset = UNSET
        if not isinstance(self.academic_subject, Unset):
            academic_subject = self.academic_subject.value


        in_language: str | Unset = UNSET
        if not isinstance(self.in_language, Unset):
            in_language = self.in_language.value


        adoption_status: str | Unset = UNSET
        if not isinstance(self.adoption_status, Unset):
            adoption_status = self.adoption_status.value


        date_modified: None | str | Unset
        if isinstance(self.date_modified, Unset):
            date_modified = UNSET
        elif isinstance(self.date_modified, datetime.date):
            date_modified = self.date_modified.isoformat()
        else:
            date_modified = self.date_modified

        notes: None | str | Unset
        if isinstance(self.notes, Unset):
            notes = UNSET
        else:
            notes = self.notes


        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "caseIdentifierUUID": case_identifier_uuid,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
            "isCurrent": is_current,
        })
        if case_identifier_uri is not UNSET:
            field_dict["caseIdentifierURI"] = case_identifier_uri
        if name is not UNSET:
            field_dict["name"] = name
        if description is not UNSET:
            field_dict["description"] = description
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if academic_subject is not UNSET:
            field_dict["academicSubject"] = academic_subject
        if in_language is not UNSET:
            field_dict["inLanguage"] = in_language
        if adoption_status is not UNSET:
            field_dict["adoptionStatus"] = adoption_status
        if date_modified is not UNSET:
            field_dict["dateModified"] = date_modified
        if notes is not UNSET:
            field_dict["notes"] = notes

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        case_identifier_uuid = UUID(d.pop("caseIdentifierUUID"))




        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

        is_current = d.pop("isCurrent")

        case_identifier_uri = d.pop("caseIdentifierURI", UNSET)

        def _parse_name(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        name = _parse_name(d.pop("name", UNSET))


        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))


        _jurisdiction = d.pop("jurisdiction", UNSET)
        jurisdiction: JurisdictionENUM | Unset
        if isinstance(_jurisdiction,  Unset):
            jurisdiction = UNSET
        else:
            jurisdiction = JurisdictionENUM(_jurisdiction)




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




        _adoption_status = d.pop("adoptionStatus", UNSET)
        adoption_status: AdoptionStatusENUM | Unset
        if isinstance(_adoption_status,  Unset):
            adoption_status = UNSET
        else:
            adoption_status = AdoptionStatusENUM(_adoption_status)




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


        def _parse_notes(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        notes = _parse_notes(d.pop("notes", UNSET))


        standards_framework = cls(
            identifier=identifier,
            case_identifier_uuid=case_identifier_uuid,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            is_current=is_current,
            case_identifier_uri=case_identifier_uri,
            name=name,
            description=description,
            jurisdiction=jurisdiction,
            academic_subject=academic_subject,
            in_language=in_language,
            adoption_status=adoption_status,
            date_modified=date_modified,
            notes=notes,
        )


        standards_framework.additional_properties = d
        return standards_framework

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
