from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.academic_subject_enum import AcademicSubjectENUM
from ..models.grade_level_enum import GradeLevelENUM
from ..models.jurisdiction_enum import JurisdictionENUM
from ..models.language_enum import LanguageENUM
from ..models.normalized_statement_type_enum import NormalizedStatementTypeENUM
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID
import datetime






T = TypeVar("T", bound="StandardsFrameworkItem")



@_attrs_define
class StandardsFrameworkItem:
    """ Individual element within a standards framework (e.g., standards, organizational groupings)

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            case_identifier_uuid (UUID): CASE Network UUID for the resource
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            has_children (bool): Whether this item has 1+ direct child standards
            case_identifier_uri (str | Unset): URI referencing the CASE Network equivalent
            statement_code (None | str | Unset): Code that identifies a standard within its standards framework (e.g.,
                "3.NF.A.1", "A.1B", "MP1"); `null` for organizational groupings without assigned codes
            description (None | str | Unset): Full text of the standard describing what students should know or be able to
                do
            statement_type (None | str | Unset): Original classification label that preserves the terminology in the state's
                official standards document (e.g., "Domain", "Cluster", "Strand", "Benchmark", "Practice Standard")
            normalized_statement_type (NormalizedStatementTypeENUM | Unset): Classification label that has been standardized
                across standards frameworks for cross-state queries and categorization
            jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
            academic_subject (AcademicSubjectENUM | Unset): Academic subject area
            grade_level (list[GradeLevelENUM] | None | Unset):
            in_language (LanguageENUM | Unset): Language used in the resource (BCP 47 format)
            date_modified (datetime.date | None | Unset): Date last modified
            notes (None | str | Unset): (Optional) Additional context, commentary, clarifications, or usage guidance
     """

    identifier: str
    case_identifier_uuid: UUID
    author: str
    provider: str
    license_: str
    attribution_statement: str
    has_children: bool
    case_identifier_uri: str | Unset = UNSET
    statement_code: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    statement_type: None | str | Unset = UNSET
    normalized_statement_type: NormalizedStatementTypeENUM | Unset = UNSET
    jurisdiction: JurisdictionENUM | Unset = UNSET
    academic_subject: AcademicSubjectENUM | Unset = UNSET
    grade_level: list[GradeLevelENUM] | None | Unset = UNSET
    in_language: LanguageENUM | Unset = UNSET
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

        has_children = self.has_children

        case_identifier_uri = self.case_identifier_uri

        statement_code: None | str | Unset
        if isinstance(self.statement_code, Unset):
            statement_code = UNSET
        else:
            statement_code = self.statement_code

        description: None | str | Unset
        if isinstance(self.description, Unset):
            description = UNSET
        else:
            description = self.description

        statement_type: None | str | Unset
        if isinstance(self.statement_type, Unset):
            statement_type = UNSET
        else:
            statement_type = self.statement_type

        normalized_statement_type: str | Unset = UNSET
        if not isinstance(self.normalized_statement_type, Unset):
            normalized_statement_type = self.normalized_statement_type.value


        jurisdiction: str | Unset = UNSET
        if not isinstance(self.jurisdiction, Unset):
            jurisdiction = self.jurisdiction.value


        academic_subject: str | Unset = UNSET
        if not isinstance(self.academic_subject, Unset):
            academic_subject = self.academic_subject.value


        grade_level: list[str] | None | Unset
        if isinstance(self.grade_level, Unset):
            grade_level = UNSET
        elif isinstance(self.grade_level, list):
            grade_level = []
            for grade_level_type_0_item_data in self.grade_level:
                grade_level_type_0_item = grade_level_type_0_item_data.value
                grade_level.append(grade_level_type_0_item)


        else:
            grade_level = self.grade_level

        in_language: str | Unset = UNSET
        if not isinstance(self.in_language, Unset):
            in_language = self.in_language.value


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
            "hasChildren": has_children,
        })
        if case_identifier_uri is not UNSET:
            field_dict["caseIdentifierURI"] = case_identifier_uri
        if statement_code is not UNSET:
            field_dict["statementCode"] = statement_code
        if description is not UNSET:
            field_dict["description"] = description
        if statement_type is not UNSET:
            field_dict["statementType"] = statement_type
        if normalized_statement_type is not UNSET:
            field_dict["normalizedStatementType"] = normalized_statement_type
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if academic_subject is not UNSET:
            field_dict["academicSubject"] = academic_subject
        if grade_level is not UNSET:
            field_dict["gradeLevel"] = grade_level
        if in_language is not UNSET:
            field_dict["inLanguage"] = in_language
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

        has_children = d.pop("hasChildren")

        case_identifier_uri = d.pop("caseIdentifierURI", UNSET)

        def _parse_statement_code(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        statement_code = _parse_statement_code(d.pop("statementCode", UNSET))


        def _parse_description(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        description = _parse_description(d.pop("description", UNSET))


        def _parse_statement_type(data: object) -> None | str | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            return cast(None | str | Unset, data)

        statement_type = _parse_statement_type(d.pop("statementType", UNSET))


        _normalized_statement_type = d.pop("normalizedStatementType", UNSET)
        normalized_statement_type: NormalizedStatementTypeENUM | Unset
        if isinstance(_normalized_statement_type,  Unset):
            normalized_statement_type = UNSET
        else:
            normalized_statement_type = NormalizedStatementTypeENUM(_normalized_statement_type)




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




        def _parse_grade_level(data: object) -> list[GradeLevelENUM] | None | Unset:
            if data is None:
                return data
            if isinstance(data, Unset):
                return data
            try:
                if not isinstance(data, list):
                    raise TypeError()
                grade_level_type_0 = []
                _grade_level_type_0 = data
                for grade_level_type_0_item_data in (_grade_level_type_0):
                    grade_level_type_0_item = GradeLevelENUM(grade_level_type_0_item_data)



                    grade_level_type_0.append(grade_level_type_0_item)

                return grade_level_type_0
            except (TypeError, ValueError, AttributeError, KeyError):
                pass
            return cast(list[GradeLevelENUM] | None | Unset, data)

        grade_level = _parse_grade_level(d.pop("gradeLevel", UNSET))


        _in_language = d.pop("inLanguage", UNSET)
        in_language: LanguageENUM | Unset
        if isinstance(_in_language,  Unset):
            in_language = UNSET
        else:
            in_language = LanguageENUM(_in_language)




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


        standards_framework_item = cls(
            identifier=identifier,
            case_identifier_uuid=case_identifier_uuid,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            has_children=has_children,
            case_identifier_uri=case_identifier_uri,
            statement_code=statement_code,
            description=description,
            statement_type=statement_type,
            normalized_statement_type=normalized_statement_type,
            jurisdiction=jurisdiction,
            academic_subject=academic_subject,
            grade_level=grade_level,
            in_language=in_language,
            date_modified=date_modified,
            notes=notes,
        )


        standards_framework_item.additional_properties = d
        return standards_framework_item

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
