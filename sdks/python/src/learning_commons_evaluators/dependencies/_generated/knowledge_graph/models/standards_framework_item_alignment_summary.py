from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..models.jurisdiction_enum import JurisdictionENUM
from ..types import UNSET, Unset
from typing import cast
from uuid import UUID






T = TypeVar("T", bound="StandardsFrameworkItemAlignmentSummary")



@_attrs_define
class StandardsFrameworkItemAlignmentSummary:
    """ A StandardsFrameworkItemSummary augmented with the educational alignment type from the source resource (lesson,
    activity, or assessment) to this standard.

        Attributes:
            case_identifier_uuid (UUID): CASE Network UUID for the resource
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            statement_code (None | str | Unset): Code that identifies a standard within its standards framework (e.g.,
                "3.NF.A.1", "A.1B", "MP1"); `null` for organizational groupings without assigned codes
            description (None | str | Unset): Full text of the standard describing what students should know or be able to
                do
            jurisdiction (JurisdictionENUM | Unset): U.S. state, territory, or multi-state designation
            curriculum_alignment_type (list[str] | Unset): Description of how the resource relates to its standard (e.g.,
                `addressing`, `building_toward`, `building_on`, `practicing`)
     """

    case_identifier_uuid: UUID
    author: str
    provider: str
    license_: str
    attribution_statement: str
    statement_code: None | str | Unset = UNSET
    description: None | str | Unset = UNSET
    jurisdiction: JurisdictionENUM | Unset = UNSET
    curriculum_alignment_type: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        case_identifier_uuid = str(self.case_identifier_uuid)

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

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

        jurisdiction: str | Unset = UNSET
        if not isinstance(self.jurisdiction, Unset):
            jurisdiction = self.jurisdiction.value


        curriculum_alignment_type: list[str] | Unset = UNSET
        if not isinstance(self.curriculum_alignment_type, Unset):
            curriculum_alignment_type = self.curriculum_alignment_type




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "caseIdentifierUUID": case_identifier_uuid,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
        })
        if statement_code is not UNSET:
            field_dict["statementCode"] = statement_code
        if description is not UNSET:
            field_dict["description"] = description
        if jurisdiction is not UNSET:
            field_dict["jurisdiction"] = jurisdiction
        if curriculum_alignment_type is not UNSET:
            field_dict["curriculumAlignmentType"] = curriculum_alignment_type

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        case_identifier_uuid = UUID(d.pop("caseIdentifierUUID"))




        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

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


        _jurisdiction = d.pop("jurisdiction", UNSET)
        jurisdiction: JurisdictionENUM | Unset
        if isinstance(_jurisdiction,  Unset):
            jurisdiction = UNSET
        else:
            jurisdiction = JurisdictionENUM(_jurisdiction)




        curriculum_alignment_type = cast(list[str], d.pop("curriculumAlignmentType", UNSET))


        standards_framework_item_alignment_summary = cls(
            case_identifier_uuid=case_identifier_uuid,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            statement_code=statement_code,
            description=description,
            jurisdiction=jurisdiction,
            curriculum_alignment_type=curriculum_alignment_type,
        )


        standards_framework_item_alignment_summary.additional_properties = d
        return standards_framework_item_alignment_summary

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
