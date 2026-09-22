from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeVar, BinaryIO, TextIO, TYPE_CHECKING, Generator

from attrs import define as _attrs_define
from attrs import field as _attrs_field

from ..types import UNSET, Unset

from ..types import UNSET, Unset
from typing import cast






T = TypeVar("T", bound="ActivitySummary")



@_attrs_define
class ActivitySummary:
    """ A lightweight representation of an Activity containing only essential identifying information for alignment
    endpoints.

        Attributes:
            identifier (str): Unique identifier for the resource in Knowledge Graph
            name (str): Name or title of the resource
            author (str): Author or creator of the resource
            provider (str): Source data provider for the resource
            license_ (str): URL to the resource's license document
            attribution_statement (str): Statement that acknowledges the resource's author and provider, as required by the
                CC BY 4.0 license
            ordinal_name (str | Unset): Label with sequence number and descriptive text (e.g., "Activity 1")
            curriculum_alignment_type (list[str] | Unset): Description of how the resource relates to its standard (e.g.,
                `addressing`, `building_toward`, `building_on`, `practicing`)
     """

    identifier: str
    name: str
    author: str
    provider: str
    license_: str
    attribution_statement: str
    ordinal_name: str | Unset = UNSET
    curriculum_alignment_type: list[str] | Unset = UNSET
    additional_properties: dict[str, Any] = _attrs_field(init=False, factory=dict)





    def to_dict(self) -> dict[str, Any]:
        identifier = self.identifier

        name = self.name

        author = self.author

        provider = self.provider

        license_ = self.license_

        attribution_statement = self.attribution_statement

        ordinal_name = self.ordinal_name

        curriculum_alignment_type: list[str] | Unset = UNSET
        if not isinstance(self.curriculum_alignment_type, Unset):
            curriculum_alignment_type = self.curriculum_alignment_type




        field_dict: dict[str, Any] = {}
        field_dict.update(self.additional_properties)
        field_dict.update({
            "identifier": identifier,
            "name": name,
            "author": author,
            "provider": provider,
            "license": license_,
            "attributionStatement": attribution_statement,
        })
        if ordinal_name is not UNSET:
            field_dict["ordinalName"] = ordinal_name
        if curriculum_alignment_type is not UNSET:
            field_dict["curriculumAlignmentType"] = curriculum_alignment_type

        return field_dict



    @classmethod
    def from_dict(cls: type[T], src_dict: Mapping[str, Any]) -> T:
        d = dict(src_dict)
        identifier = d.pop("identifier")

        name = d.pop("name")

        author = d.pop("author")

        provider = d.pop("provider")

        license_ = d.pop("license")

        attribution_statement = d.pop("attributionStatement")

        ordinal_name = d.pop("ordinalName", UNSET)

        curriculum_alignment_type = cast(list[str], d.pop("curriculumAlignmentType", UNSET))


        activity_summary = cls(
            identifier=identifier,
            name=name,
            author=author,
            provider=provider,
            license_=license_,
            attribution_statement=attribution_statement,
            ordinal_name=ordinal_name,
            curriculum_alignment_type=curriculum_alignment_type,
        )


        activity_summary.additional_properties = d
        return activity_summary

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
